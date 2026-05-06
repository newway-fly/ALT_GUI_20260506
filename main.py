# main.py
# -*- coding: utf-8 -*-
import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# 核心模块
from core.system_controller import SystemController
from utils.main_cb import MainCB

def main():
    # 1. 设置高分屏适配 (必需在创建 QApplication 之前)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    app = QApplication(sys.argv)
    
    
    # 2. 启动核心控制器 (Model & Logic)
    sys_ctrl = SystemController()
    
    # 3. 启动主界面 (View)
    main_window = MainCB(controller=sys_ctrl)
    main_window.show()
    
    # 4. 进入事件循环
    exit_code = app.exec_()
    
    # 5. 退出清理
    sys_ctrl.cleanup()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()