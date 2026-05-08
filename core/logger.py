# core/logger.py
import logging
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from PyQt5.QtCore import QObject, pyqtSignal

# 定义日志保存目录 (会自动创建 logs 文件夹)
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

class QtLogHandler(logging.Handler, QObject):
    """
    自定义 Log Handler：
    拦截 logging 模块发出的日志，通过 Qt 信号转发给 UI 线程。
    这样 UI 界面就可以直接连接这个信号来显示日志。
    """
    sig_log = pyqtSignal(str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        """当有日志产生时被调用"""
        try:
            msg = self.format(record)
            # 发送信号给 UI 线程 (线程安全)
            self.sig_log.emit(msg)
        except Exception:
            self.handleError(record)

def setup_logger():
    """
    初始化全局 Logger 配置
    返回: qt_handler 实例 (用于在 UI 层连接信号)
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO) # 设定最低捕获级别 (INFO, WARNING, ERROR)

    # 1. 定义统一的日志格式: [时间] [级别]: 消息
    formatter = logging.Formatter(
        fmt='[%(asctime)s] %(levelname)-5s: %(message)s',
        datefmt='%H:%M:%S'
    )

    # 清除旧的 handlers (防止重复打印)
    if logger.hasHandlers():
        logger.handlers.clear()

    # 2. 控制台输出 Handler (Console) -> 方便开发调试
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 3. 文件输出 Handler (按天轮转) -> 方便长期追溯
    # 每天生成一个新文件 (run_20260209.log)，保留最近 30 天
    file_name = os.path.join(LOG_DIR, f"run_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = TimedRotatingFileHandler(
        filename=file_name,
        when="D",       # 按天切分
        interval=1,     # 1天一个
        backupCount=30, # 保留30个文件
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 4. GUI 输出 Handler (Qt Signal) -> 方便界面显示
    qt_handler = QtLogHandler()
    qt_handler.setFormatter(formatter)
    logger.addHandler(qt_handler)

    return qt_handler 

# 全局单例对象，方便其他模块直接引用
# 用法: from core.logger import log
# log.info("message")
log = logging.getLogger()