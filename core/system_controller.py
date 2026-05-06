# core/system_controller.py
# -*- coding: utf-8 -*-
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread
from queue import Queue, Empty
from collections import namedtuple
import time
import re

from core.protocol import Protocol, CmdType
from driver.serial_worker import SerialWorker
from core.logger import log 

# 定义任务结构
Task = namedtuple('Task', ['cmd_type', 'args', 'timeout', 'wait_for_ack', 'callback'])

class SystemController(QObject):
    # --- 信号定义 ---
    sig_stm_ack = pyqtSignal(str)             # STM32 ACK消息
    sig_stm_info = pyqtSignal(str)            # 通用显示信息 (Log用)
    # 410 业务数据信号
    sig_dither_read = pyqtSignal(str, int)  # [新增] 通道名, 值

    # STM32 电源数据更新 (字典格式)
    sig_stm_power_data = pyqtSignal(dict)
    
    
    # STM32 DAC 读取返回 (通道, 值)
    sig_stm_dac_read = pyqtSignal(int, int)
    
    # 410 业务数据信号
    sig_410_lock_data = pyqtSignal(float, float) 
    sig_410_dac_update = pyqtSignal(int, int)    
    sig_410_scan_point = pyqtSignal(int, float)  
    sig_adc_update = pyqtSignal(int, float)
    

    # 驱动信号
    sig_driver_write = pyqtSignal(bytes)
    sig_driver_connect = pyqtSignal(str, object) 
    sig_driver_close = pyqtSignal()
    sig_conn_status = pyqtSignal(int, str)
    sig_bulk_data_ready = pyqtSignal(str, object)

    def __init__(self):
        super().__init__()


        # --- 大块数据内存截获器 ---
        self.bulk_mode = None  # 状态: 'P22', 'NNQ_XQ', 'SCAN_1' 等
        self.bulk_buffer = []  # 内存池
        self.bulk_dict = {}    # 用于暂存 6 通道的 NNQ 或 Scan 数据
        
        # # 抛出给 UI 的信号: (数据类型, 数组/字典)
        # self.sig_bulk_data_ready = pyqtSignal(str, object)


        self.task_queue = Queue()
        self.current_task = None
        self.is_waiting_ack = False
        
        self.Print_Flag = True
        self.ack_timeout_timer = QTimer()
        self.ack_timeout_timer.setSingleShot(True)
        self.ack_timeout_timer.timeout.connect(self._on_ack_timeout)

        self.driver_thread = QThread()
        self.worker = SerialWorker()
        self.worker.moveToThread(self.driver_thread)
        
        self.sig_driver_write.connect(self.worker.write_data)
        self.sig_driver_connect.connect(self.worker.connect_port)
        self.sig_driver_close.connect(self.worker.close_port)
        
        self.worker.sig_data_received.connect(self._handle_incoming_data)
        self.worker.sig_connected.connect(self._on_worker_connected)
        self.worker.sig_error_occurred.connect(lambda e: log.error(f"Serial Error: {e}"))
        
        self.driver_thread.start()
        
        # STM32 ADC 数据批处理
        self._stm_adc_buffer = {}
        self.stm_batch_timer = QTimer()
        self.stm_batch_timer.setInterval(80) 
        self.stm_batch_timer.setSingleShot(True)
        self.stm_batch_timer.timeout.connect(self._on_stm_batch_timeout)

        self.pump_timer = QTimer()
        self.pump_timer.timeout.connect(self._process_queue)
        self.pump_timer.start(20)

    def open_device(self, port, settings):
        log.info(f"Connecting to {port} with: {settings}")
        self.sig_driver_connect.emit(port, settings)

    def close_device(self):
        log.info("Disconnecting...")
        self.sig_driver_close.emit()

    def send_cmd(self, cmd_type: CmdType, *args, timeout=1000, wait_for_ack=True, callback=None):
        task = Task(cmd_type, args, timeout, wait_for_ack, callback)
        self.task_queue.put(task)

    def _process_queue(self):
        if self.is_waiting_ack: return
        try:
            task = self.task_queue.get_nowait()
            self._execute_task(task)
        except Empty: pass

    def _execute_task(self, task: Task):
        self.current_task = task
        try:
            payload = Protocol.pack(task.cmd_type, *task.args)
        except Exception as e:
            log.error(f"Pack Error: {e}")
            self.current_task = None
            return
        
        self.sig_driver_write.emit(payload)
        log.info(f">> TX: {payload.strip().decode('ascii', errors='ignore')}")

        if task.wait_for_ack:
            self.is_waiting_ack = True
            self.ack_timeout_timer.start(task.timeout)
        else:
            self.is_waiting_ack = False
            self.current_task = None

    def _on_ack_timeout(self):
        if self.current_task:
            log.warning(f"Timeout waiting ACK for: {self.current_task.cmd_type.name}")
        self.is_waiting_ack = False
        self.current_task = None

    def _handle_incoming_data(self, raw_line):
        source, content = Protocol.parse_line(raw_line)

        if not source and raw_line.strip():
            source = "RAW"
            content = raw_line.strip()

        if not source: return

        # =================================================================
        # === [极速关卡] 大块波形数据内存拦截器 (RAM Interceptor) ===
        # =================================================================
        if "----BEGIN_" in content:
            if "BEGIN_DATA" in content:
                self.bulk_mode = "P22"
            elif "BEGIN_NNQ_" in content:
                ch = content.split("_")[-1].strip("-")
                self.bulk_mode = f"NNQ_{ch}"
            elif "BEGIN_SCAN" in content:
                # 兼容 "BEGIN_SCAN_1" 
                # 使用正则提取里面的数字 1~6
                match = re.search(r'\d+', content)
                if match:
                    ch_num = match.group()
                    # 【核心修复】映射表: 1:XI, 2:XQ, 3:YI, 4:YQ, 5:XP, 6:YP
                    ch_map = {'1':'XI', '2':'XQ', '3':'YI', '4':'YQ', '5':'XP', '6':'YP'}
                    ch_name = ch_map.get(ch_num, f"CH{ch_num}")
                else:
                    ch_name = "UNKNOWN"
                self.bulk_mode = f"SCAN_{ch_name}"
            
            self.bulk_buffer = []  # 开启新的内存池
            return                 # 绝对拦截，不往下走

        if "----END_" in content:
            if "END_DATA" in content:
                # 单个大数组接收完毕，抛给 GUI
                self.sig_bulk_data_ready.emit("P22", self.bulk_buffer)
                
            elif "END_NNQ" in content:
                if self.bulk_mode and self.bulk_mode.startswith("NNQ_"):
                    ch = self.bulk_mode.split("_")[-1]
                    self.bulk_dict[ch] = self.bulk_buffer
                    if len(self.bulk_dict) == 6:  # 6个通道收齐
                        self.sig_bulk_data_ready.emit("NNQ", self.bulk_dict)
                        self.bulk_dict = {}
                    
            elif "END_SCAN" in content:  # 【核心修复】匹配真实的结束符
                if self.bulk_mode and self.bulk_mode.startswith("SCAN_"):
                    ch = self.bulk_mode.split("_")[-1]  # 此时这里已经是 'XI', 'XQ' 等名字了
                    self.bulk_dict[ch] = self.bulk_buffer
                    if len(self.bulk_dict) == 6:
                        self.sig_bulk_data_ready.emit("SCAN", self.bulk_dict)
                        self.bulk_dict = {}
                    
            self.bulk_mode = None  # 关闭吃数据模式
            return                 # 绝对拦截

        # 如果正处于大块数据接收状态，把纯数字吃进内存池
        if self.bulk_mode is not None:
            try:
                # 兼容逗号或空格分割的多数据行
                parts = content.replace(',', ' ').split()
                
                # 如果是 NNQ 扫描，我们期望它是一对 (X, Y) 数据
                if self.bulk_mode.startswith("NNQ_") and len(parts) >= 2:
                    x_val = float(parts[0])
                    y_val = float(parts[1])
                    self.bulk_buffer.append((x_val, y_val)) # 存入元组 (DA, PD)
                else:
                    # 传统的 1D 数据 (P22 或 SCAN_CH)
                    for p in parts:
                        self.bulk_buffer.append(float(p))
            except ValueError:
                pass  # 过滤掉偶尔混入的非数字字符
            return  # 吃完数据后立刻拦截！
        # =================================================================

        # 如果正处于大块数据接收状态，把纯数字吃进内存池
        # === [修复] 大块波形数据内存拦截器 - 支持 2D 数据 ===
        if self.bulk_mode is not None:
            try:
                # 兼容逗号或空格分割的多数据行 (例如 "825,0.00711" 或 "0.0123")
                parts = content.replace(',', ' ').split()
                
                # 如果是 NNQ 扫描，我们期望它是一对 (X, Y) 数据
                if self.bulk_mode.startswith("NNQ_") and len(parts) >= 2:
                    x_val = float(parts[0])
                    y_val = float(parts[1])
                    self.bulk_buffer.append((x_val, y_val)) # 存入元组 (DA, PD)
                else:
                    # 传统的 1D 数据 (P22 或 SCAN_CH)
                    for p in parts:
                        self.bulk_buffer.append(float(p))
            except ValueError:
                pass  # 过滤掉偶尔混入的非数字字符
            return  # 绝对拦截
        # =================================================================


        # === 1. 解析 STM32 ADC Power 数据 ===
        # 格式: "ADC_HEATER_VCC : 2704"
        if "ADC_" in content and ":" in content:
            adc_match = re.match(r"(ADC_\w+)\s*:\s*(\d+)", content)
            if adc_match:
                # [新增] 必须先发射Info信号，确保在Log窗口能看到 "ADC_xxx: yyy"
                self.sig_stm_info.emit(content)
                
                key = adc_match.group(1)
                val = int(adc_match.group(2))
                self._stm_adc_buffer[key] = val
                self.stm_batch_timer.start()
                return

        # === 2. 解析 STM32 DAC 读取返回 ===
        # 针对: "ACK:DAC 1=1613 2=372 3=1240" (包含在ACK行中，需在ACK Return前解析)
        if "DAC" in content:
            pairs = re.findall(r"(\d+)\s*=\s*(\d+)", content)
            if pairs:
                for ch_str, val_str in pairs:
                    try:
                        self.sig_stm_dac_read.emit(int(ch_str), int(val_str))
                    except: pass
            
        # === [修改点] 解析 410 Dither 读取返回 ===
        # 格式: "Resp: DITHER XP_I 15"
        if "Resp: DITHER" in content:
            match = re.search(r"DITHER\s+(\w+)\s+(\d+)", content)
            if match:
                ch_name = match.group(1)
                val = int(match.group(2))
                # 触发信号给 UI 更新文本框
                self.sig_dither_read.emit(ch_name, val)
                # 发送给文本框显示
                self.sig_stm_info.emit(f"410: {content}")
                # 【修改点：删除这里的 return！让 log 正常打印】

        # === 3. ACK 检查 ===
        is_ack = False
        upper_c = content.upper()
        if "ACK" in upper_c or "POWER ALL" in upper_c:
            is_ack = True
            if "ADC POWER" in upper_c:
                self._stm_adc_buffer.clear()

        if is_ack:
            log.info(f"<< RX Get\n{content}")

            if self.is_waiting_ack:
                self.ack_timeout_timer.stop()
                self.is_waiting_ack = False
                if self.current_task and self.current_task.callback:
                    self.current_task.callback(True)
                self.current_task = None
            return

        # === 4. 数据分发 ===
        if source == "STM":
            self.sig_stm_ack.emit(content)
            self.sig_stm_info.emit(content)

        elif source == "410":
            self._parse_410_data(content)
            
        else:
            self.sig_stm_info.emit(f"RAW: {content}")

    def _on_stm_batch_timeout(self):
        """STM32 Power ADC 数据接收完毕，打包发送"""
        if self._stm_adc_buffer:
            # 只要有 ADC_ 开头的数据，就打包发给 MainCB
            # 由 MainCB 根据数据量决定是否计算功耗
            self.sig_stm_power_data.emit(self._stm_adc_buffer.copy())
            # 发送后不清空buffer，防止后续逻辑需要积累，
            # 但为了防止 ADC 1 和 ADC Power 混淆，建议依靠 MainCB 的覆盖更新机制
            # 这里选择清理 buffer，确保每次 batch 都是新的
            self._stm_adc_buffer.clear()

    def _parse_410_data(self, text):
        try:
            if "Scan:" in text: pass 
            elif text.startswith("L:"): pass
            elif "ADC" in text.upper() or "CH" in text.upper():
                match = re.search(r"(?:ADC|CH).*?(\d+).*?([\d\.]+)", text, re.IGNORECASE)
                if match:
                    ch = int(match.group(1))
                    val = float(match.group(2))
                    self.sig_adc_update.emit(ch, val)
                    log.info(f"Parsed 410 ADC Ch{ch} = {val:.3f}V")
                else:
                    log.info(f"410 ADC Raw: {text}")
            else:
                log.info(f"410: {text}")
        except Exception as e:
            log.error(f"Parse Error: {e}")

    def _on_worker_connected(self, success, msg):
        if success:
            log.info(f"SerialPort {msg}")
            self.sig_conn_status.emit(1, msg)
        else:
            log.warning(f"SerialPort {msg}")
            self.is_waiting_ack = False
            self.current_task = None
            self.sig_conn_status.emit(0, msg)

    def cleanup(self):
        self.driver_thread.quit()
        self.driver_thread.wait()