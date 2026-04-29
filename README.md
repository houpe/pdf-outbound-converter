# WMS 出库单转换工具

将PDF/Excel出库单转换为标准OMS出库Excel格式的Web应用，支持多种商家模板一键转换。

## 功能特性

- 📄 **PDF解析**: 自动提取PDF出库单中的头部信息和商品明细
- 📊 **多模板支持**: 内置黔寨寨、黎明屯、欢乐牧场 3种模板
- 🔀 **商品拆零路由**: 根据 SQLite 拆零配置自动将数量分配到二级单位或最小单位
- 🧩 **商品拆零管理**: 支持页面内直接新增/编辑编码、切换是否拆零、保存到数据库、查看创建时间、确认删除
- 📝 **转换日志**: 每次转换自动记录（JSONL格式），可通过 `/api/logs` 查询统计
- ⬇️ **自动下载**: 转换完成后自动下载结果文件
- 🖥️ **Web界面**: 基于React + Vite，支持拖拽上传
- ⚡ **异步处理**: FastAPI后端高效处理转换
- 🌐 **远程访问**: 支持多人同时使用

## 支持的模板

| 模板 | 输入格式 | 商户编码 | 说明 |
|------|----------|----------|------|
| 黔寨寨贵州烙锅 | PDF | Q20260427013 | 解析PDF中的头部信息和商品表格 |
| 黎明屯铁锅炖 | Excel | Q20260427017 | 门店信息从导入模板的「收货机构」字段读取 |
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

### 商品拆零规则

商品拆零配置存储在后端 SQLite 数据库 `web/backend/split_codes.db`，通过页面底部「拆零管理」入口维护，不再从 `商品拆零模板.xlsx` 读取业务配置。

| 是否拆零 | 数量填入列 | 说明 |
|----------|-----------|------|
| 是 | I列（二级单位） | 需要拆零的商品 |
| 否 | J列（最小单位） | 直接以最小销售单位发货 |
| 未配置 | I列（二级单位） | 默认按拆零处理 |

#### 拆零校验策略

| 模板 | 是否校验拆零管理中存在编码 | 说明 |
|------|----------------------------|------|
| 黔寨寨贵州烙锅 | 否 | 转换时不阻断 |
| 黎明屯铁锅炖 | 是 | 缺失编码时弹窗提示，可在弹窗内选择拆零/不拆零并保存后重试 |
| 欢乐牧场 | 否 | 转换时不阻断 |

#### 拆零管理页面

- 支持直接在表格内维护「商品编码」和「是否拆零」。
- 点击「保存」后写入 SQLite 数据库。
- 新增记录自动生成创建时间，列表按创建时间倒序展示。
- 删除记录使用页面内确认弹窗，点击「确认删除」后立即从数据库删除，点击「取消」不生效。

## 项目结构

```
wms表格转换2/
├── web/                    # Web应用
│   ├── backend/            # FastAPI后端
│   │   ├── main.py         # 后端主程序（转换逻辑）
│   │   ├── requirements.txt# Python依赖
│   │   ├── uploads/        # 上传临时目录
│   │   ├── downloads/      # 下载结果目录
│   │   ├── split_codes.db  # 商品拆零 SQLite 数据库（运行时生成）
│   │   └── conversion_log.jsonl  # 转换日志
│   └── frontend/           # React+Vite前端
├── templates/              # Excel模板文件
│   ├── OMS出库.xlsx        # 输出模板
│   ├── 商品拆零模板.xlsx    # 历史配置模板（当前运行逻辑不读取）
│   ├── 黎明屯铁锅炖模板.xlsx
│   └── 欢乐牧场模板.xlsx
└── README.md
```

## 本地开发

### 后端

```bash
cd web/backend
pip install -r requirements.txt
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
- 后端路径：`/www/wwwroot/wms-api/`（端口 8000，PM2 `wms-api`）
- 前端路径：`/www/wwwroot/address-weight-calc/wms/`
- nginx 配置：宝塔面板 `address-weight.conf`

### 一键部署脚本

从项目根目录执行：

```bash
# 配置服务器信息（建议写入环境变量或 .env 文件）
WMS_SERVER="${WMS_SERVER:-root@your-server.com}"
WMS_API_PATH="${WMS_API_PATH:-/www/wwwroot/wms-api}"
WMS_FRONT_PATH="${WMS_FRONT_PATH:-/www/wwwroot/address-weight-calc/wms}"

# 1. 构建前端
cd web/frontend && npm run build

# 2. 部署后端
scp ../../web/backend/main.py "$WMS_SERVER:$WMS_API_PATH/main.py"

# 3. 部署前端
scp -r ./dist/* "$WMS_SERVER:$WMS_FRONT_PATH/"

# 4. 重启服务
ssh "$WMS_SERVER" "pm2 restart wms-api && echo ✅ done"
```

### 快捷部署（单条命令）

从项目 `web/frontend` 目录执行：

```bash
WMS_SERVER="${WMS_SERVER:-root@your-server.com}" && npm run build && scp -r dist/* "$WMS_SERVER:/www/wwwroot/address-weight-calc/wms/" && scp ../../web/backend/main.py "$WMS_SERVER:/www/wwwroot/wms-api/main.py" && ssh "$WMS_SERVER" 'pm2 restart wms-api && echo ✅ done'
```

### PM2 启动方式

服务器使用 PM2 托管 FastAPI 后端，推荐启动命令：

```bash
cd /www/wwwroot/wms-api
pm2 start 'python3 -m uvicorn main:app --host 0.0.0.0 --port 8000' --name wms-api
pm2 save
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
| F | 收货机构/店铺名 |
| G | 商品名称 |
| H | 商家商品编码 |
| I | 二级单位数量 |
| J | 最小单位数量 |

## 转换日志

每次转换完成后自动记录到 `conversion_log.jsonl`，支持查询接口：

```bash
# 查询最近50条日志
curl 'https://www.houpe.top/wms/api/logs?limit=50'

# 本地直接查看
cat web/backend/conversion_log.jsonl | jq .
```

日志字段包含：时间、模板、文件名、商品数、涉及店铺数、商品合计数量、各店铺名称、输出文件名、状态、错误信息等。

## 版本历史

- v3.5 - 商品拆零配置改为 SQLite 页面维护；拆零管理支持内联新增/编辑/保存、创建时间倒序、页面内确认删除；黎明屯缺失编码支持弹窗内配置并重试；仅黎明屯转换校验拆零配置
- v3.4 - 修复拆零路由：新增模板回退查找逻辑；LMT门店信息从模板「收货机构」读取
- v3.3 - 新增转换日志（JSONL）、拆零模板自动路由、转换成功后自动下载
- v3.2 - 安全加固：路径遍历防护、lifespan 替换废弃 API、清理端点移除、requirements 合并
- v3.1 - 后端优化：CORS 限定来源、动态模板获取、流式上传、TTL 清理、文件限制
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
