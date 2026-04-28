# WMS 出库单转换工具

将PDF/Excel出库单转换为标准OMS出库Excel格式的Web应用，支持多种商家模板一键转换。

## 功能特性

- 📄 **PDF解析**: 自动提取PDF出库单中的头部信息和商品明细
- 📊 **多模板支持**: 内置黔寨寨、黎明屯、欢乐牧场 3种模板
- 🖥️ **Web界面**: 基于React + Vite，支持拖拽上传
- ⚡ **异步处理**: FastAPI后端高效处理转换
- 🌐 **远程访问**: 支持多人同时使用

## 支持的模板

| 模板 | 输入格式 | 商户编码 | 说明 |
|------|----------|----------|------|
| 黔寨寨贵州烙锅 | PDF | Q20260427013 | 解析PDF中的头部信息和商品表格 |
| 黎明屯铁锅炖 | Excel | Q20260427017 | 门店信息自动从文件名提取（如：`12.25江门利和-配送发货单PS2512210002001.xlsx` → 门店：江门利和） |
| 欢乐牧场 | Excel | Q20260427015 | 自动识别店铺列，按店铺合并输出 |

## 默认编码

### 商户编码（输出Excel - B列）

每家商户固定不同，切换模板时自动填充：

| 模板 | 商户编码 |
|------|----------|
| 黔寨寨贵州烙锅 | Q20260427013 |
| 黎明屯铁锅炖 | Q20260427017 |
| 欢乐牧场 | Q20260427015 |

### 仓库编码（输出Excel - C列 供货机构）

默认值：`ZTOWHHY001`

## 项目结构

```
wms表格转换2/
├── web/                    # Web应用
│   ├── backend/            # FastAPI后端
│   │   ├── main.py         # 后端主程序（转换逻辑）
│   │   ├── requirements.txt# Python依赖
│   │   ├── uploads/        # 上传临时目录
│   │   └── downloads/      # 下载结果目录
│   └── frontend/           # React+Vite前端
├── templates/              # Excel模板文件
└── README.md
```

## 本地开发

### 后端

```bash
cd web/backend
pip install -r requirements.txt
cp ../../templates/*.xlsx .
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd web/frontend
npm install
npm run dev
```

## 部署（服务器）

### 服务器环境

- 访问地址：`https://www.houpe.top/wms/`
- 后端路径：`/www/wwwroot/wms-api/main.py`（端口 8000，PM2 `wms-api`）
- 前端路径：`/www/wwwroot/address-weight-calc/wms/`
- nginx 配置：宝塔面板 `address-weight.conf`

### 一键部署脚本

从本地执行（推荐，已测试通过）：

```bash
# 1. 构建前端
cd web/frontend && npm run build

# 2. 部署
ssh root@www.houpe.top << 'DEPLOY'
# 更新前端
rm -rf /www/wwwroot/address-weight-calc/wms/assets /www/wwwroot/address-weight-calc/wms/index.html
DEPLOY

scp -r ./dist/* root@www.houpe.top:/www/wwwroot/address-weight-calc/wms/
scp ./web/backend/main.py root@www.houpe.top:/www/wwwroot/wms-api/main.py

ssh root@www.houpe.top << 'RESTART'
cp /root/wms-转换2/templates/*.xlsx /www/wwwroot/wms-api/ 2>/dev/null || echo "skip templates"
cd /www/wwwroot/wms-api && pm2 restart wms-api
echo "✅ 部署完成"
RESTART
```

### 完整一键脚本（单条命令）

```bash
cd web/frontend && npm run build && scp -r dist/* root@www.houpe.top:/www/wwwroot/address-weight-calc/wms/ && scp web/backend/main.py root@www.houpe.top:/www/wwwroot/wms-api/main.py && ssh root@www.houpe.top 'cd /www/wwwroot/wms-api && pm2 restart wms-api && echo ✅ done' && git add . && git commit -m "update" && git push origin main
```

### nginx 配置参考（已在 address-weight.conf 中）

```nginx
# WMS 前端 - /www/wwwroot/address-weight-calc/wms/
location = /wms { rewrite ^/wms$ /wms/ permanent; }
location /wms/ {
    alias /www/wwwroot/address-weight-calc/wms/;
    try_files $uri $uri/ /wms/index.html;
}

# WMS API 反向代理 - 后端端口 8000
location /wms/api/ {
    proxy_pass http://127.0.0.1:8000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    client_max_body_size 50m;
}

# WMS 下载文件代理
location /wms/downloads/ {
    proxy_pass http://127.0.0.1:8000/downloads/;
    proxy_set_header Host $host;
}
```

## 输出格式

所有模板统一输出为标准 `OMS出库.xlsx` 格式:

| 列 | 内容 |
|----|------|
| A | 单据编号 |
| B | 商户编码 |
| C | 供货机构 |
| D | (空) |
| E | 收货人,电话,地址 |
| F | 商品编码 |
| G | (空) |
| H | 数量 |
| I | 收货机构/店铺名 |
| J | 商品名称 |

## 版本历史

- v3.0 - 重构为Web应用（FastAPI + React），删除桌面端代码
- v2.3 - 重构项目目录 (src/assets/templates)，欢乐牧场合并输出
- v2.2 - 新增欢乐牧场模板
- v2.1 - 新增黎明屯铁锅炖模板
- v2.0 - 多模板下拉选择器
- v1.3 - 优化异步处理和日志显示
- v1.2 - 双平台打包支持
- v1.1 - GUI界面
- v1.0 - 基础PDF转Excel

## 许可证

MIT License

## 作者

houpe
