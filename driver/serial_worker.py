# driver/serial_worker.py
# -*- coding: utf-8 -*-
from PyQt5.QtCore import QObject, pyqtSignal, QIODevice
from PyQt5.QtSerialPort import QSerialPort

class SerialWorker(QObject):
    """
    [驱动层] 串口工作者 (基于 QSerialPort 优化版)
    支持完整的串口参数配置 (波特率, 数据位, 校验位, 停止位, 流控)
    """
    sig_connected = pyqtSignal(bool, str)     
    sig_data_received = pyqtSignal(str)       
    sig_error_occurred = pyqtSignal(str)      

    def __init__(self):
        super().__init__()
        self.serial = None

    def connect_port(self, port_name, settings):
        """
        连接串口
        :param port_name: 串口号 (e.g., "COM3")
        :param settings: 配置字典 或 仅波特率(int)
        """
        # --- [健壮性修复] 兼容旧接口 (如果传入的是 int，自动转为字典) ---
        if isinstance(settings, int):
            settings = {'baud': settings}
        elif not isinstance(settings, dict):
            # 默认兜底
            settings = {'baud': 115200}

        if self.serial:
            self.close_port()
        
        self.serial = QSerialPort()
        self.serial.setPortName(port_name)
        
        # --- 1. 配置波特率 ---
        self.serial.setBaudRate(int(settings.get('baud', 115200)))
        
        # --- 2. 配置数据位 ---
        d_bits = int(settings.get('data_bits', 8))
        if d_bits == 5: self.serial.setDataBits(QSerialPort.Data5)
        elif d_bits == 6: self.serial.setDataBits(QSerialPort.Data6)
        elif d_bits == 7: self.serial.setDataBits(QSerialPort.Data7)
        else: self.serial.setDataBits(QSerialPort.Data8)
        
        # --- 3. 配置校验位 ---
        parity_str = str(settings.get('parity', 'None')).title()
        if parity_str == 'Even': self.serial.setParity(QSerialPort.EvenParity)
        elif parity_str == 'Odd': self.serial.setParity(QSerialPort.OddParity)
        elif parity_str == 'Space': self.serial.setParity(QSerialPort.SpaceParity)
        elif parity_str == 'Mark': self.serial.setParity(QSerialPort.MarkParity)
        else: self.serial.setParity(QSerialPort.NoParity)
        
        # --- 4. 配置停止位 ---
        stop_str = str(settings.get('stop_bits', '1'))
        if stop_str == '1.5': self.serial.setStopBits(QSerialPort.OneAndHalfStop)
        elif stop_str == '2': self.serial.setStopBits(QSerialPort.TwoStop)
        else: self.serial.setStopBits(QSerialPort.OneStop)
        
        # --- 5. 配置流控 ---
        flow_str = str(settings.get('flow', 'None')).title()
        if flow_str == 'Hardware': self.serial.setFlowControl(QSerialPort.HardwareControl)
        elif flow_str == 'Software': self.serial.setFlowControl(QSerialPort.SoftwareControl)
        else: self.serial.setFlowControl(QSerialPort.NoFlowControl)
        
        # --- 打开串口 ---
        if self.serial.open(QIODevice.ReadWrite):
            # 格式化一下连接信息方便调试
            # info = f"{port_name}@{settings.get('baud')} {d_bits}{parity_str[0]}{stop_str}"
            info = f"{port_name}@{settings.get('baud')}"
            self.sig_connected.emit(True, f"Connected {info}")
            
            self.serial.readyRead.connect(self._on_ready_read)
            self.serial.errorOccurred.connect(self._on_error)
        else:
            self.sig_connected.emit(False, f"Open Fail: {self.serial.errorString()}")
            self.serial.deleteLater()
            self.serial = None

    def close_port(self):
        """关闭串口"""
        if self.serial and self.serial.isOpen():
            self.serial.close()
            self.sig_connected.emit(False, "Disconnected by User")
        
        if self.serial:
            self.serial.deleteLater()
            self.serial = None

    def write_data(self, data: bytes):
        """发送数据"""
        if self.serial and self.serial.isOpen():
            self.serial.write(data)
        else:
            self.sig_error_occurred.emit("Write Error: Port not open")

    def _on_ready_read(self):
        """接收回调"""
        if not self.serial: return
        while self.serial.canReadLine():
            raw_data = self.serial.readLine()
            try:
                text = bytes(raw_data).decode('utf-8', errors='ignore').strip()
                if text:
                    self.sig_data_received.emit(text)
            except Exception as e:
                self.sig_error_occurred.emit(f"Decode Error: {e}")

    def _on_error(self, error_code):
        """错误回调"""
        if error_code == QSerialPort.NoError: return
        error_msg = self.serial.errorString()
        
        if error_code in [QSerialPort.ResourceError, QSerialPort.PermissionError]:
            self.sig_error_occurred.emit(f"Critical: {error_msg}")
            if self.serial and self.serial.isOpen():
                self.serial.close()
                self.sig_connected.emit(False, f"Dropped: {error_msg}")
        else:
            self.sig_error_occurred.emit(f"Warning: {error_msg}")





    def parse_incoming_data(self, raw_str):
        """
        【协议截获】：拦截 STM32 的 MAOM 回复
        """
        # 假设 STM32 读寄存器返回格式为 "\r\n0xXXXX"
        if "0x" in raw_str: 
            try:
                # 1. 物理切片：提取 "0x" 后面的纯 Hex 字符串
                hex_val = raw_str.strip().split("0x")[-1]
                
                # 2. 内存回填：直接写入主线程共享的 DRV_Rx_Array
                # 注意：需确保 serial_worker 能访问到 main_window 对象
                self.main_window.DRV_Rx_Array[0] = hex_val 
                
                # 3. 异步握手：通知 DRV_Control_Pane 数据已就绪
                # 触发其 Drv_TxFinish_Check 槽函数打印日志
                self.main_window.drv_pane.Drv_TxFinish_flag.emit("DRV Read", True, [1, True, False])
                
            except Exception as e:
                print(f"DRV 协议解析异常: {e}")