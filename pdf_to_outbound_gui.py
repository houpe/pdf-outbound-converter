#!/usr/bin/env python3.10
"""
PDF出库单转Excel工具 - PySide6桌面版
"""

import pdfplumber
import openpyxl
import re
import os
import sys
import threading
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                                QHBoxLayout, QLabel, QLineEdit, QPushButton,
                                QTextEdit, QGroupBox, QFileDialog, QMessageBox,
                                QProgressBar, QGridLayout, QFrame)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QIcon


def resource_path(relative_path):
    """Return absolute path to a bundled resource for PyInstaller."""
    if getattr(sys, 'frozen', False):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

class ConversionWorker(QThread):
    log = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, pdf_path, output_path, merchant_code, template_path):
        super().__init__()
        self.pdf_path = pdf_path
        self.output_path = output_path
        self.merchant_code = merchant_code
        self.template_path = template_path

    def run(self):
        try:
            self.log.emit(f"正在读取PDF: {self.pdf_path}")
            header_info, items = extract_pdf_data(self.pdf_path)

            self.log.emit("\n提取的头部信息:")
            labels = {
                'order_no': '单据编号', 'receiver_org': '收货机构',
                'supplier_org': '供货机构', 'receiver_name': '收货人',
                'receiver_phone': '收货电话', 'receiver_address': '收货地址',
                'order_date': '订单日期'
            }
            for key, value in header_info.items():
                self.log.emit(f"  {labels.get(key, key)}: {value}")

            self.log.emit(f"\n商品明细 ({len(items)}条):")
            for item in items:
                self.log.emit(f"  {item['item_code']} - {item['item_name']} x {item['quantity']} {item['unit']}")

            self.log.emit("\n正在生成Excel...")
            create_excel(header_info, items, self.template_path, self.output_path, self.merchant_code)

            self.log.emit(f"\n转换完成! 共处理 {len(items)} 条记录")
            self.log.emit(f"\n提示: 双击转换后的Excel文件即可打开编辑")
            self.finished.emit(True, self.output_path)
        except Exception as e:
            self.log.emit(f"\n错误: {str(e)}")
            self.finished.emit(False, str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF出库单转Excel工具")
        self.setMinimumSize(700, 550)

        # 使用资源路径，以支持打包后的可执行文件
        self.template_path = resource_path('OMS出库.xlsx')

        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(12)

        # 文件设置组
        file_group = QGroupBox("文件设置")
        file_layout = QGridLayout(file_group)
        file_layout.setSpacing(10)

        file_layout.addWidget(QLabel("PDF文件:"), 0, 0)
        self.pdf_edit = QLineEdit()
        self.pdf_edit.setPlaceholderText("选择PDF出库单文件...")
        self.pdf_edit.setStyleSheet("QLineEdit { padding: 5px; border: 1px solid #ccc; border-radius: 4px; }")
        file_layout.addWidget(self.pdf_edit, 0, 1)

        pdf_btn = QPushButton("浏览")
        pdf_btn.setFixedWidth(70)
        pdf_btn.clicked.connect(self.select_pdf)
        file_layout.addWidget(pdf_btn, 0, 2)

        file_layout.addWidget(QLabel("输出路径:"), 1, 0)
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("自动生成默认文件名...")
        self.output_edit.setStyleSheet("QLineEdit { padding: 5px; border: 1px solid #ccc; border-radius: 4px; }")
        file_layout.addWidget(self.output_edit, 1, 1)

        output_btn = QPushButton("浏览")
        output_btn.setFixedWidth(70)
        output_btn.clicked.connect(self.select_output)
        file_layout.addWidget(output_btn, 1, 2)

        file_layout.addWidget(QLabel("商户编码:"), 2, 0)
        self.merchant_edit = QLineEdit()
        self.merchant_edit.setPlaceholderText("请输入商户编码")
        self.merchant_edit.setStyleSheet("QLineEdit { padding: 5px; border: 1px solid #ccc; border-radius: 4px; }")
        file_layout.addWidget(self.merchant_edit, 2, 1)

        main_layout.addWidget(file_group)

        # 转换按钮
        btn_layout = QHBoxLayout()
        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #217346;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 30px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #1e6b40; }
            QPushButton:pressed { background-color: #1a5c37; }
            QPushButton:disabled { background-color: #a0a0a0; }
        """)
        self.convert_btn.clicked.connect(self.start_conversion)
        btn_layout.addWidget(self.convert_btn)
        btn_layout.setAlignment(Qt.AlignCenter)
        main_layout.addLayout(btn_layout)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("QProgressBar { height: 4px; border: none; background: #e0e0e0; border-radius: 2px; } QProgressBar::chunk { background: #217346; border-radius: 2px; }")
        main_layout.addWidget(self.progress)

        # 日志组
        log_group = QGroupBox("转换日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #333;
                border-radius: 4px;
                font-family: "Menlo", "Monaco", "Consolas", monospace;
                font-size: 12px;
                line-height: 1.4;
            }
        """)
        log_layout.addWidget(self.log_text)
        main_layout.addWidget(log_group)

    def select_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择PDF文件", "", "PDF files (*.pdf)")
        if path:
            self.pdf_edit.setText(path)
            if not self.output_edit.text():
                base = os.path.splitext(path)[0]
                self.output_edit.setText(f"{base}_转换结果.xlsx")

    def select_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存Excel文件", "", "Excel files (*.xlsx)")
        if path:
            self.output_edit.setText(path)

    def start_conversion(self):
        pdf_path = self.pdf_edit.text().strip()
        output_path = self.output_edit.text().strip()
        merchant_code = self.merchant_edit.text().strip()

        if not pdf_path:
            QMessageBox.warning(self, "警告", "请选择PDF文件")
            return
        if not os.path.exists(pdf_path):
            QMessageBox.critical(self, "错误", f"找不到文件: {pdf_path}")
            return
        if not output_path:
            QMessageBox.warning(self, "警告", "请设置输出路径")
            return
        if not os.path.exists(self.template_path):
            QMessageBox.critical(self, "错误", f"找不到模板文件: {self.template_path}")
            return

        self.convert_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.log_text.clear()

        self.worker = ConversionWorker(pdf_path, output_path, merchant_code, self.template_path)
        self.worker.log.connect(self.append_log)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def append_log(self, text):
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def on_finished(self, success, message):
        self.progress.setVisible(False)
        self.convert_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "成功", f"转换完成!\n输出文件: {message}")
        else:
            QMessageBox.critical(self, "错误", message)


def extract_pdf_data(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        all_tables = []
        for page in pdf.pages:
            full_text += page.extract_text() or ""
            tables = page.extract_tables()
            all_tables.extend(tables)
    return parse_header(full_text), parse_items(all_tables)


def parse_header(text):
    info = {}
    match = re.search(r'单据编号[：:]\s*(\S+)', text)
    info['order_no'] = match.group(1) if match else ''
    match = re.search(r'收货机构[：:]\s*([^  ]+?)(?=\s+[^\s：:]+[：:]|$)', text)
    info['receiver_org'] = match.group(1).strip() if match else ''
    match = re.search(r'供货机构[：:]\s*([^  ]+?)(?=\s+[^\s：:]+[：:]|$)', text)
    info['supplier_org'] = match.group(1).strip() if match else ''
    match = re.search(r'收货人[：:]\s*([^  ]+?)(?=\s+[^\s：:]+[：:]|$)', text)
    info['receiver_name'] = match.group(1).strip() if match else ''
    match = re.search(r'收货电话[：:]\s*(\d+)', text)
    info['receiver_phone'] = match.group(1) if match else ''
    match = re.search(r'收货地址[：:]\s*(.+?)(?=\n|$)', text)
    info['receiver_address'] = match.group(1).strip() if match else ''
    match = re.search(r'订单日期[：:]\s*(\S+)', text)
    info['order_date'] = match.group(1) if match else ''
    return info


def parse_items(tables):
    items = []
    for table in tables:
        for row in table:
            if not row or len(row) < 6:
                continue
            first_cell = str(row[0]).strip()
            if not first_cell.isdigit():
                continue
            item = {
                'category': str(row[1]).strip() if row[1] else '',
                'item_code': str(row[2]).strip() if row[2] else '',
                'item_name': str(row[3]).strip() if row[3] else '',
                'spec': str(row[4]).strip().replace('\n', '') if row[4] else '',
                'unit': str(row[5]).strip() if row[5] else '',
                'quantity': str(row[6]).strip() if row[6] else '0',
                'remark': str(row[7]).strip() if row[7] else '',
            }
            if item['item_code'] and item['item_name']:
                items.append(item)
    return items


def create_excel(header_info, items, template_path, output_path, merchant_code=''):
    wb = openpyxl.load_workbook(template_path)
    ws = wb.active
    for row in ws.iter_rows(min_row=3, max_row=ws.max_row, min_col=1, max_col=10):
        for cell in row:
            cell.value = None
    receiver_info = f"{header_info.get('receiver_name', '')},{header_info.get('receiver_phone', '')},{header_info.get('receiver_address', '')}"
    for i, item in enumerate(items, start=3):
        ws.cell(row=i, column=1, value=header_info.get('order_no', ''))
        ws.cell(row=i, column=2, value=merchant_code)
        ws.cell(row=i, column=3, value=header_info.get('supplier_org', ''))
        ws.cell(row=i, column=4, value='')
        ws.cell(row=i, column=5, value=receiver_info)
        ws.cell(row=i, column=6, value=item['item_code'])
        ws.cell(row=i, column=7, value='')
        ws.cell(row=i, column=8, value=int(item['quantity']) if item['quantity'].isdigit() else item['quantity'])
        ws.cell(row=i, column=9, value=header_info.get('receiver_org', ''))
        ws.cell(row=i, column=10, value=item['item_name'])
    wb.save(output_path)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = None
    for ext in ['ico', 'icns', 'png']:
        candidate = os.path.join(base_dir, f'app_icon.{ext}')
        if os.path.exists(candidate):
            icon_path = candidate
            break
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
