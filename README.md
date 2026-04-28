# PDF出库单转Excel工具

将PDF出库单/配送单转换为OMS出库Excel格式的桌面应用工具。

## 功能特性

- 📄 **PDF解析**: 自动提取PDF出库单中的头部信息和商品明细
- 📊 **Excel转换**: 按OMS出库模板格式生成Excel文件
- 🖥️ **GUI界面**: 基于PySide6的简洁桌面界面，支持文件选择和实时日志
- ⚡ **异步处理**: 后台线程处理转换，界面保持响应
- 🍎 **跨平台**: 支持 macOS 和 Windows 双平台打包

## 项目结构

```
wms表格转换2/
├── src/                        # 源代码
│   ├── main.py                 # GUI主程序 (PySide6)
│   ├── cli.py                  # CLI版本 (命令行)
│   └── convert_icon.py         # 图标转换工具
├── assets/                     # 图标资源
│   ├── icon_source.png         # 原始图标
│   ├── icon.icns               # macOS应用图标
│   ├── app_icon.icns           # macOS应用图标 (备份)
│   └── app_icon.iconset/       # 图标资源集
├── templates/                  # Excel模板
│   ├── OMS出库.xlsx            # 黔寨寨出库模板
│   ├── 黎明屯铁锅炖模板.xlsx
│   └── 欢乐牧场模板.xlsx
├── PDF出库单转换.spec          # macOS打包配置
├── PDF出库单转换_Windows.spec  # Windows打包配置
├── build_windows.bat           # Windows构建脚本
├── requirements.txt
└── README.md
```

## 环境要求

- Python 3.10+
- PySide6
- pdfplumber
- openpyxl
- PyInstaller (打包发布)

## 安装依赖

```bash
pip install pyside6 pdfplumber openpyxl pyinstaller pillow
```

## 使用方法

### GUI版本

```bash
python src/main.py
```

操作步骤:
1. 点击"浏览"选择PDF出库单文件
2. 设置输出Excel文件路径 (默认自动生成)
3. 输入商户编码
4. 点击"开始转换"
5. 查看转换日志，确认完成

### CLI版本

```bash
python src/cli.py [PDF路径] [输出路径]
```

运行后会提示输入商户编码，然后自动完成转换。

## 打包发布

### macOS

```bash
# 生成图标资源
iconutil -c icns assets/app_icon.iconset

# 打包
pyinstaller --clean PDF出库单转换.spec
```

输出: `dist/PDF出库单转换.app`

### Windows

```bash
# 方法1: 使用构建脚本
build_windows.bat

# 方法2: 手动打包
python convert_icon.py  # 生成app_icon.ico
pyinstaller --clean PDF出库单转换_Windows.spec
```

输出: `dist/PDF出库单转换/PDF出库单转换.exe`

## 数据提取说明

### 头部信息提取

工具会从PDF中自动提取以下字段:

| 字段 | 说明 |
|------|------|
| 单据编号 | 出库单编号 |
| 收货机构 | 收货方组织 |
| 供货机构 | 供货方组织 |
| 收货人 | 收货人姓名 |
| 收货电话 | 收货人联系电话 |
| 收货地址 | 收货详细地址 |
| 订单日期 | 出库日期 |

### 商品明细提取

从PDF表格中提取商品信息:

| 字段 | 说明 |
|------|------|
| category | 商品分类 |
| item_code | 商品编码 |
| item_name | 商品名称 |
| spec | 商品规格 |
| unit | 单位 |
| quantity | 数量 |
| remark | 备注 |

## 输出格式

生成的Excel文件遵循 `OMS出库.xlsx` 模板格式:

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
| I | 收货机构 |
| J | 商品名称 |

## 技术架构

- **UI框架**: PySide6 (Qt for Python)
- **PDF解析**: pdfplumber (基于pdfminer)
- **Excel处理**: openpyxl
- **打包工具**: PyInstaller
- **异步处理**: QThread (Qt线程)

## 常见问题

### PDF解析失败

确保PDF文件包含可识别的文本和表格结构。部分扫描版PDF可能无法正确解析。

### 打包体积过大

PyInstaller打包会包含完整的PySide6和Python运行环境，正常体积在100-300MB左右。

### Windows打包图标不显示

确保 `app_icon.ico` 文件存在，或运行 `convert_icon.py` 从PNG生成。

## 版本历史

- v1.0 - 基础PDF转Excel功能
- v1.1 - 添加GUI界面
- v1.2 - 支持双平台打包
- v1.3 - 优化异步处理和日志显示

## 许可证

MIT License

## 作者

houpe