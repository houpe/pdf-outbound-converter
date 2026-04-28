# 出库单转换工具

将PDF/Excel出库单转换为标准OMS出库Excel格式的桌面应用，支持多种商家模板一键转换。

## 功能特性

- 📄 **PDF解析**: 自动提取PDF出库单中的头部信息和商品明细
- 📊 **多模板支持**: 内置黔寨寨、黎明屯、欢乐牧场 3种模板，下拉框一键切换
- 🖥️ **GUI界面**: 基于PySide6的现代化桌面界面，支持文件选择和实时日志
- ⚡ **异步处理**: 后台线程处理转换，界面保持响应
- 🍎 **跨平台**: 支持 macOS 和 Windows 双平台打包

## 支持的模板

| 模板 | 输入格式 | 说明 |
|------|----------|------|
| 黔寨寨贵州烙锅 | PDF | 解析PDF中的头部信息和商品表格 |
| 黎明屯铁锅炖 | Excel | 读取指定行/列的订单信息 |
| 欢乐牧场 | Excel | 自动识别店铺列（单位与下单后结余之间），按店铺合并输出 |

## 项目结构

```
wms表格转换2/
├── src/                        # 源代码
│   ├── main.py                 # GUI主程序
│   ├── cli.py                  # CLI版本
│   └── convert_icon.py         # 图标转换工具
├── assets/                     # 图标资源
├── templates/                  # Excel模板
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
- PyInstaller

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
1. 选择对应模板（黔寨寨 / 黎明屯 / 欢乐牧场）
2. 选择输入文件（PDF或Excel）
3. 设置输出路径（默认自动生成）
4. 输入商户编码
5. 点击"开始转换"

### CLI版本

```bash
python src/cli.py [PDF路径] [输出路径]
```

## 打包发布

### macOS

```bash
iconutil -c icns assets/app_icon.iconset
pyinstaller --clean PDF出库单转换.spec
```

输出: `dist/PDF出库单转换.app`

> **注意**: PyInstaller 签名失败时需手动修复:
> ```bash
> xattr -cr dist/PDF出库单转换.app
> codesign --force --deep --sign - dist/PDF出库单转换.app
> ```

### Windows

```bash
build_windows.bat
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

## 常见问题

### PDF解析失败
确保PDF包含可识别文本和表格结构，扫描版PDF可能无法正确解析。

### 打包体积过大
PyInstaller包含完整Python运行环境，正常体积100-300MB。

### 欢乐牧场转换
Excel中"单位"和"下单后结余"之间的列为店铺名，系统自动识别有数量(>0)的店铺列并合并输出。

## 版本历史

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
