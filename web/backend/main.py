#!/usr/bin/env python3
"""
WMS PDF/Excel 转换工具 - FastAPI 后端入口
将PDF/Excel出库单转换为标准OMS出库Excel格式。
"""

import logging
import os
import re
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from config import (
    ALLOWED_ORIGINS, BASE_DIR, DOWNLOADS_DIR, DOWNLOAD_TTL_SECONDS,
    HEADER_FIELD_LABELS, TEMPLATES, DB_PATH, OMS_TEMPLATE, SPLIT_TEMPLATE,
)
from database import get_db, init_db
from schemas import SplitCodeCreate, BatchItem
from services.conversion import _do_convert, create_excel
from services.logging_svc import _safe_log, LOG_FIELDS
from middleware.rate_limit import _check_rate_limit, _rate_limit_store, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX
from parsers.base import _extract_shop_name, _extract_header_value

# --- 启动与关闭 ---


def cleanup_expired_downloads():
    """删除超过 TTL 的下载文件"""
    now = time.time()
    for f in DOWNLOADS_DIR.iterdir():
        if f.is_file() and now - f.stat().st_mtime > DOWNLOAD_TTL_SECONDS:
            f.unlink()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化拆零数据库并清理过期下载文件"""
    init_db()
    cleanup_expired_downloads()
    import asyncio
    async def _periodic_cleanup():
        while True:
            await asyncio.sleep(3600)
            try:
                cleanup_expired_downloads()
            except Exception:
                pass
    task = asyncio.create_task(_periodic_cleanup())
    yield
    task.cancel()


app = FastAPI(title="WMS PDF/Excel 转换服务", version="3.5.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
    expose_headers=[],
    max_age=600,
)

# --- 路由 ---


@app.get("/api/templates")
def list_templates():
    return {
        "templates": [
            {
                "key": key,
                "name": cfg["name"],
                "accept": cfg["accept"],
                "default_merchant_code": cfg["merchant_code"],
            }
            for key, cfg in TEMPLATES.items()
        ]
    }


@app.post("/api/convert")
async def convert_file(
    files: list[UploadFile] = File(...),
    template_key: str = Form(...),
    merchant_code: str = Form(default=""),
):
    template_cfg = TEMPLATES.get(template_key)
    file_names = [f.filename for f in files]
    log_record = {
        "status": "error",
        "template_key": template_key,
        "template_name": template_cfg["name"] if template_cfg else None,
        "file_names": file_names,
        "file_count": len(files),
    }
    try:
        # 限流检查
        client_ip = os.environ.get("X-Forwarded-For", "127.0.0.1")
        _check_rate_limit(client_ip)

        if merchant_code and len(merchant_code) > 64:
            raise HTTPException(status_code=400, detail="商户编码过长（最多64字符）")
        if merchant_code and not re.match(r'^[A-Za-z0-9_-]+$', merchant_code):
            raise HTTPException(status_code=400, detail="商户编码只能包含字母、数字、下划线和连字符")

        result = await _do_convert(files, template_key, merchant_code, template_cfg)
        log_record["status"] = "success"
        log_record["output_filename"] = result["filename"]
        log_record["item_count"] = result["item_count"]
        log_record["parsed_files"] = result["parsed_files"]
        log_record["store_count"] = result["store_count"]
        log_record["total_quantity"] = result["total_quantity"]
        log_record["stores_list"] = result.get("stores_list", [])
        _safe_log(log_record)
        return result
    except HTTPException as e:
        log_record["error"] = e.detail if isinstance(e.detail, str) else str(e.detail)
        log_record["http_status"] = e.status_code
        _safe_log(log_record)
        raise
    except Exception as e:
        log_record["error"] = str(e)
        _safe_log(log_record)
        raise


@app.get("/api/version")
def get_version_history():
    from database import get_db
    conn = get_db()
    rows = conn.execute("SELECT version, date, changes FROM version_history ORDER BY version DESC").fetchall()
    conn.close()
    history = []
    for row in rows:
        history.append({
            "version": row["version"],
            "date": row["date"],
            "changes": [c.strip() for c in row["changes"].split(";") if c.strip()],
        })
    return {"version": history[0]["version"] if history else "unknown", "history": history}


@app.get("/api/logs/stats")
def get_logs_stats():
    from config import LOG_FILE
    if not LOG_FILE.exists():
        return {
            "total_conversions": 0, "success_count": 0, "error_count": 0,
            "total_files": 0, "total_items": 0, "total_stores": 0,
            "total_quantity": 0, "template_stats": [],
        }
    import json
    entries = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    total = len(entries)
    success = sum(1 for e in entries if e.get("status") == "success")
    errors = sum(1 for e in entries if e.get("status") == "error")
    total_files = sum(int(e.get("file_count", 0) or 0) for e in entries if e.get("status") == "success")
    total_items = sum(int(e.get("item_count", 0) or 0) for e in entries if e.get("status") == "success")
    total_stores = sum(int(e.get("store_count", 0) or 0) for e in entries if e.get("status") == "success")
    total_quantity = 0
    for e in entries:
        if e.get("status") == "success":
            tq = e.get("total_quantity", 0)
            if tq is None:
                continue
            try:
                total_quantity += int(float(str(tq).replace(",", "")))
            except (ValueError, TypeError):
                pass

    tmpl_map = {}
    for e in entries:
        if e.get("status") != "success":
            continue
        tk = e.get("template_key", "unknown")
        tn = e.get("template_name", tk)
        if tk not in tmpl_map:
            tmpl_map[tk] = {"key": tk, "name": tn, "count": 0, "files": 0, "items": 0, "stores": 0}
        tmpl_map[tk]["count"] += 1
        tmpl_map[tk]["files"] += int(e.get("file_count", 0) or 0)
        tmpl_map[tk]["items"] += int(e.get("item_count", 0) or 0)
        tmpl_map[tk]["stores"] += int(e.get("store_count", 0) or 0)

    return {
        "total_conversions": total,
        "success_count": success,
        "error_count": errors,
        "total_files": total_files,
        "total_items": total_items,
        "total_stores": total_stores,
        "total_quantity": total_quantity,
        "template_stats": sorted(tmpl_map.values(), key=lambda x: x["count"], reverse=True),
    }


# --- 拆零配置 CRUD ---


@app.get("/api/split-codes")
def list_split_codes():
    conn = get_db()
    cur = conn.execute("SELECT code, split, item_name, created_at FROM split_codes ORDER BY created_at DESC")
    codes = [{"code": row["code"], "split": row["split"], "item_name": row["item_name"], "created_at": row["created_at"]} for row in cur]
    conn.close()
    return {"codes": codes, "total": len(codes)}


@app.post("/api/split-codes")
def create_split_code(input: SplitCodeCreate):
    if input.split not in ("是", "否"):
        raise HTTPException(status_code=400, detail="拆零值必须为「是」或「否」")
    if not input.code.strip():
        raise HTTPException(status_code=400, detail="商品编码不能为空")
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO split_codes (code, split) VALUES (?, ?)",
            (input.code.strip(), input.split)
        )
        conn.commit()
        return {"success": True, "code": input.code.strip(), "split": input.split}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail=f"商品编码 {input.code} 已存在")
    finally:
        conn.close()


@app.delete("/api/split-codes/{code:path}")
def delete_split_code(code: str):
    conn = get_db()
    cur = conn.execute("DELETE FROM split_codes WHERE LOWER(code) = LOWER(?)", (code.strip(),))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"商品编码 {code} 未找到")
    return {"success": True, "deleted": code.strip()}


@app.put("/api/split-codes/{old_code:path}")
def update_split_code(old_code: str, input: SplitCodeCreate):
    if input.split not in ("是", "否"):
        raise HTTPException(status_code=400, detail="拆零值必须为「是」或「否」")
    if not input.code.strip():
        raise HTTPException(status_code=400, detail="商品编码不能为空")
    conn = get_db()
    cur = conn.execute(
        "UPDATE split_codes SET code = ?, split = ? WHERE LOWER(code) = LOWER(?)",
        (input.code.strip(), input.split, old_code.strip())
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"商品编码 {old_code} 未找到")
    return {"success": True, "old_code": old_code.strip(), "code": input.code.strip(), "split": input.split}


@app.patch("/api/split-codes/batch")
def batch_upsert_split_codes(items: list[BatchItem] = Body(...)):
    conn = get_db()
    success = []
    errors = []
    for item in items:
        code = item.code.strip()
        if not code:
            errors.append({"id": item.id, "error": "编码不能为空"})
            continue
        if item.split not in ("是", "否"):
            errors.append({"id": item.id, "error": "拆零值必须为「是」或「否」"})
            continue
        try:
            if not item.id:
                conn.execute(
                    "INSERT INTO split_codes (code, split, created_at) VALUES (?, ?, datetime('now', 'localtime'))",
                    (code, item.split)
                )
                success.append({"id": item.id or code, "code": code, "split": item.split, "action": "added"})
            else:
                cur = conn.execute(
                    "UPDATE split_codes SET code = ?, split = ? WHERE LOWER(code) = LOWER(?)",
                    (code, item.split, item.id)
                )
                if cur.rowcount == 0:
                    errors.append({"id": item.id, "error": f"未找到编码 {item.id}"})
                else:
                    success.append({"id": item.id, "code": code, "split": item.split, "action": "updated"})
        except sqlite3.IntegrityError:
            errors.append({"id": item.id, "error": f"商品编码 {code} 已存在"})
            conn.execute("ROLLBACK")
            conn.close()
            raise HTTPException(status_code=409, detail=errors)
    if errors:
        conn.execute("ROLLBACK")
        conn.close()
        raise HTTPException(status_code=400, detail=errors)
    conn.commit()
    conn.close()
    return {"success": True, "count": len(success), "items": success}


# --- 下载 ---


@app.get("/downloads/{filename}")
def download_file(filename: str):
    # 防止路径遍历攻击
    safe = Path(filename).name
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="非法文件名")
    filepath = DOWNLOADS_DIR / safe
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(
        path=str(filepath),
        filename=safe,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
