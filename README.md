# WMS 出库单转换工具

将PDF/Excel出库单转换为标准OMS出库Excel格式的Web应用，支持多种商家模板一键转换。

## 功能特性

- 📄 **PDF解析**: 自动提取PDF出库单中的头部信息和商品明细
- 📊 **多模板支持**: 内置黔寨寨、黎明屯、欢乐牧场、湖南尹三顺 4种模板
- 🔀 **商品拆零路由**: 根据 SQLite 拆零配置自动将数量分配到二级单位或最小单位（按仓库隔离）
- 🏭 **多仓库支持**: 仓库选择首页，不同仓库显示不同模板和拆零配置
- 🧩 **商品拆零管理**: 支持页面内直接新增/编辑编码、切换是否拆零、保存到数据库、查看创建时间、确认删除
- 📝 **转换日志**: 每次转换自动记录（JSONL格式），可通过 `/api/logs` 查询统计
- 🛡️ **API限流**: 自动限制请求频率，防止滥用
- ⬇️ **自动下载**: 转换完成后自动下载结果文件
- 🖥️ **Web界面**: 基于React + Vite，支持拖拽上传
- ⚡ **异步处理**: FastAPI后端高效处理转换
- 🧪 **测试覆盖**: 70+ pytest 测试用例覆盖解析/转换/CRUD/限流
- 🌐 **远程访问**: 支持多人同时使用

## 支持的模板

| 模板 | 输入格式 | 商户编码 | 仓库 | 说明 |
|------|----------|----------|------|------|
| 黔寨寨贵州烙锅 | PDF | Q20260427013 | 武汉汉阳仓 (ZTOWHHY001) | 解析PDF中的头部信息和商品表格 |
| 黎明屯铁锅炖 | Excel | Q20260427017 | 武汉汉阳仓 (ZTOWHHY001) | 门店信息从导入模板的「收货机构」字段读取 |
| 欢乐牧场 | Excel | Q20260427015 | 武汉汉阳仓 (ZTOWHHY001) | 自动识别店铺列，按店铺合并输出 |
| 湖南尹三顺 | Excel | Q20260526001 | 长沙雨花二仓 (ZTOCSYH002) | WMS汇总单格式，支持拆零管理 |

## 仓库配置

访问 `/wms/` 显示仓库选择首页，点击进入对应仓库。

| 仓库编码 | 仓库名称 | 可用模板 |
|----------|----------|----------|
| ZTOWHHY001 | 武汉汉阳仓 | 黔寨寨、黎明屯、欢乐牧场 |
| ZTOCSYH002 | 长沙雨花二仓 | 湖南尹三顺 |

仓库信息在 `web/backend/config.json` 的 `warehouses` 和 `template_groups` 字段中配置，可扩展。

## 默认编码

### 商户编码（输出Excel - B列）

每家商户固定不同，切换模板时自动填充：

| 模板 | 商户编码 |
|------|----------|
| 黔寨寨贵州烙锅 | Q20260427013 |
| 黎明屯铁锅炖 | Q20260427017 |
| 欢乐牧场 | Q20260427015 |

### 仓库编码（输出Excel - C列 供货机构）

| 仓库 | 编码 |
|------|------|
| 武汉汉阳仓 | ZTOWHHY001 |
| 长沙雨花二仓 | ZTOCSYH002 |

### 商品拆零规则

商品拆零配置存储在后端 SQLite 数据库 `web/backend/split_codes.db`，**按仓库隔离**，通过页面底部「拆零管理」入口维护。

| 是否拆零 | 数量填入列 | 说明 |
|----------|-----------|------|
| 是 | I列（二级单位） | 需要拆零的商品 |
| 否 | J列（最小单位） | 直接以最小销售单位发货 |
| 未配置 | J列（最小单位） | 默认不拆零 |

#### 拆零校验策略

| 模板 | 是否校验拆零管理中存在编码 | 说明 |
|------|----------------------------|------|
| 黔寨寨贵州烙锅 | 否 | 转换时不阻断 |
| 黎明屯铁锅炖 | 是 | 缺失编码时弹窗提示，可在弹窗内选择拆零/不拆零并保存后重试 |
| 欢乐牧场 | 否 | 转换时不阻断 |
| 湖南尹三顺 | 否 | 仅已配置拆零的产品走二级单位，其余默认最小单位 |

#### 拆零管理页面

- 支持直接在表格内维护「商品编码」和「是否拆零」。
- 点击「保存」后写入 SQLite 数据库。
- 新增记录自动生成创建时间，列表按创建时间倒序展示。
- 删除记录使用页面内确认弹窗，点击「确认删除」后立即从数据库删除，点击「取消」不生效。

## 项目结构

```
wms表格转换2/
├── web/                    # Web应用
│   ├── backend/            # FastAPI后端（模块化架构）
│   │   ├── main.py         # 路由入口（仅保留路由注册）
│   │   ├── config.py       # 配置常量（模板/路径/限流/CORS）
│   │   ├── config.json     # 可编辑配置文件
│   │   ├── database.py     # SQLite数据库操作
│   │   ├── schemas.py      # Pydantic数据模型
│   │   ├── parsers/        # 解析器模块
│   │   │   ├── base.py             # 通用解析辅助函数
│   │   │   ├── pdf_parser.py       # 黔寨寨PDF解析
│   │   │   ├── excel_parser_lmt.py # 黎明屯Excel解析
│   │   │   ├── excel_parser_hlmc.py# 欢乐牧场Excel解析
│   │   │   └── excel_parser_yss.py # 湖南尹三顺Excel解析
│   │   ├── services/       # 业务服务
│   │   │   ├── conversion.py       # 转换核心逻辑
│   │   │   └── logging_svc.py      # 转换日志服务
│   │   ├── middleware/     # 中间件
│   │   │   └── rate_limit.py       # API限流
│   │   ├── tests/          # 测试套件（70+用例）
│   │   ├── pytest.ini      # pytest配置
│   │   ├── requirements.txt# Python运行依赖
│   │   ├── uploads/        # 上传临时目录
│   │   ├── downloads/      # 下载结果目录
│   │   ├── split_codes.db  # 商品拆零SQLite数据库（运行时生成）
│   │   └── conversion_log.jsonl  # 转换日志
│   └── frontend/           # React+Vite前端
│       ├── src/
│       │   ├── App.jsx / App.css
│       │   ├── features/convert/   # 转换页面（含仓库选择首页）
│       │   ├── SplitManager.jsx / SplitManager.css
│       │   ├── ErrorBoundary.jsx / ErrorBoundary.css
│       │   ├── SplitToggle.jsx     # 共享拆零切换组件
│       │   └── Icons.jsx           # 共享图标组件集合
│       └── ...
├── templates/              # Excel模板文件
│   ├── OMS出库.xlsx        # 输出模板
│   ├── 商品拆零模板.xlsx    # 历史配置模板（当前运行逻辑不读取）
│   ├── 黎明屯铁锅炖模板.xlsx
│   └── 欢乐牧场模板.xlsx
├── requirements-dev.txt    # 开发依赖（pytest/httpx/coverage）
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

### 测试

```bash
cd web/backend
pip install -r ../../requirements-dev.txt  # 安装开发依赖
python3 -m pytest tests/ -v                 # 运行全部测试
python3 -m pytest tests/ -v --tb=short      # 简洁输出
python3 -m pytest tests/ --cov=.            # 覆盖率报告
```

## 部署（服务器）

### 服务器环境

- 访问地址：`https://www.houpe.top/wms/`（仓库选择首页）
- 后端路径：`/opt/wms/web/backend/`（端口 8000，systemd 管理 `wms-backend.service`）
- 前端路径：`/www/wwwroot/address-weight-calc/wms/`
- nginx 配置：`/www/server/panel/vhost/nginx/openclaw.conf`

### 部署方式：Docker Compose（2026-05 从 PM2 迁移）

compose 文件：`/www/docker/docker-compose.yml`

```yaml
wms-api:
  image: node:24
  restart: always
  working_dir: /app
  volumes:
    - /www/wwwroot/wms-api:/app          # 绑定挂载，Python 端
  ports:
    - "8000:8000"
  entrypoint:
    - /app/venv/bin/python3
    - -m
    - uvicorn
    - main:app
    - --host
    - 0.0.0.0
    - --port
    - "8000"
  networks:
    - app_net
```

容器名：`docker-wms-api-1`，查看日志：`docker logs docker-wms-api-1`

### 发布脚本

```bash
WMS_SERVER="${WMS_SERVER:-root@www.houpe.top}"
WMS_API_PATH="${WMS_API_PATH:-/www/wwwroot/wms-api}"
WMS_FRONT_PATH="${WMS_FRONT_PATH:-/www/wwwroot/address-weight-calc/wms}"

# 1. 构建前端
cd web/frontend && npm run build

# 2. 部署后端（模块化后的全部文件）
scp -r ../../web/backend/*.py ../../web/backend/*.json ../../web/backend/*.txt "$WMS_SERVER:$WMS_API_PATH/"
scp -r ../../web/backend/parsers/ "$WMS_SERVER:$WMS_API_PATH/parsers/"
scp -r ../../web/backend/services/ "$WMS_SERVER:$WMS_API_PATH/services/"
scp -r ../../web/backend/middleware/ "$WMS_SERVER:$WMS_API_PATH/middleware/"

# 3. 部署前端
scp -r ./dist/* "$WMS_SERVER:$WMS_FRONT_PATH/"

# 4. 重启容器（替代旧的 pm2 restart）
ssh "$WMS_SERVER" "docker restart docker-wms-api-1 && echo ✅ done"
```

### 快捷发布（单条命令）

```bash
WMS_SERVER="${WMS_SERVER:-root@www.houpe.top}" && npm run build && scp -r dist/* "$WMS_SERVER:/www/wwwroot/address-weight-calc/wms/" && scp ../../web/backend/*.py ../../web/backend/*.json ../../web/backend/*.txt "$WMS_SERVER:/www/wwwroot/wms-api/" && scp -r ../../web/backend/parsers ../../web/backend/services ../../web/backend/middleware "$WMS_SERVER:/www/wwwroot/wms-api/" && ssh "$WMS_SERVER" 'docker restart docker-wms-api-1 && echo ✅ done'
```

### nginx 配置参考（已在 openclaw.conf 中）

```nginx
# WMS 仓库选择首页
location = /wms { rewrite ^/wms$ /wms/ permanent; }

# WMS 分组路由（仓库编码 URL）
location ~ ^/wms/([A-Za-z0-9_-]+)/?$ {
    alias /www/wwwroot/address-weight-calc/wms/;
    index index.html;
    try_files $uri /wms/index.html;
}

# WMS 静态资源
location ^~ /wms/ {
    alias /www/wwwroot/address-weight-calc/wms/;
    index index.html;
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

- v4.4 - 拆零管理按仓库隔离（ZTOWHHY001/ZTOCSYH002独立配置）；新增仓库选择首页（/wms/）；ZTOWHHY001分组（黔寨寨/黎明屯/欢乐牧场）；ZTOCSYH002新增ZBWP2139/ZBWP0185默认拆零支持
- v4.3 - 新增湖南尹三顺模板（WMS汇总单格式Excel转换）；新增URL分组访问，不同路径显示不同模板
- v4.2 - 三家模板统一优化：商品数量为 0 或负数时自动排除
- v4.1 - 三家模板收件人姓名优化：单字姓名自动重复为双字
- v4.0 - 黎明屯收件人电话固定18888888888；新增190+测试套件；前端架构重构
- v3.9 - 欢乐牧场订单号重构（YYMMDD+4位随机数）；优化多文件累加选择逻辑
- v3.8 - 前端架构重构：组件化拆分，双栏工作台布局，Toast通知
- v3.7 - 首页版本号徽章，修复欢乐牧场空编码行
- v3.6 - 后端模块化重构；新增70+pytest测试；启用API限流
- v3.5 - 拆零配置改为SQLite页面维护；黎明屯缺失编码弹窗配置
- v3.0 - 重构为Web应用（FastAPI + React）
- v2.0 - 多模板下拉选择器
- v1.0 - 基础PDF转Excel

## 许可证

MIT License

## 作者

houpe
