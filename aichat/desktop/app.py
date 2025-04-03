# desktop/app.py
import sqlite3
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTextEdit, QPushButton, QLineEdit
from core.ai_chat import process_input
import asyncio

# app.py
from database import init_db, record_thought
from flask import Flask, render_template, request

app = Flask(__name__)

# 初始化数据库
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.form['user_input']
    thought = "正在分析用户输入..."
    conclusion = f"你输入了：{user_input}，这是我的回答。"
    record_thought(user_input, thought, conclusion)
    return render_template('index.html', response=conclusion)

@app.route('/history')
def history():
    conn = sqlite3.connect('datas/aichat.db')
    cursor = conn.cursor()
    cursor.execute('SELECT task, thought, conclusion, timestamp FROM thoughts ORDER BY timestamp DESC')
    records = cursor.fetchall()
    conn.close()
    return render_template('history.html', records=records)

if __name__ == '__main__':
    app.run(debug=True)

class AIChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AIChat - Windows")
        self.setGeometry(100, 100, 600, 400)

        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 输入框
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("请输入你的问题或指令")
        layout.addWidget(self.input_field)

        # 提交按钮
        self.submit_button = QPushButton("提交")
        self.submit_button.clicked.connect(self.on_submit)
        layout.addWidget(self.submit_button)

        # 输出框
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        layout.addWidget(self.output_area)

    def on_submit(self):
        user_input = self.input_field.text()
        if user_input:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(process_input(user_input))
            self.output_area.append(f"输入: {user_input}\n{result['result']}\n---")
            self.input_field.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AIChatWindow()
    window.show()
    sys.exit(app.exec_())