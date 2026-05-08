# utils/main_cb.py
# -*- coding: utf-8 -*-
import sys
import os,time
from PyQt5.QtWidgets import QWidget, QMessageBox
from PyQt5.QtCore import pyqtSlot, QSettings, QTimer
from PyQt5.QtSerialPort import QSerialPortInfo

from utils.Ui_MainWindow import Ui_MainWindow
from core.protocol import CmdType
from core.logger import setup_logger, log

from datetime import datetime
import numpy as np
from utils.analysis_windows import FFTPlotWindow, GridPlotWindow


DAC_REF_VOLT = 3.3
DAC_RESOLUTION = 4095

# 辅助系数
RATIO_HEATER = 3.0
RATIO_DRV_VCC = 3.0
RATIO_DRV_VDR = 4.0 

from core.Drv_Control_Pane import DRV_Control_Pane
from PyQt5.QtCore import pyqtSignal

class MainCB(QWidget):

    # 1. 在类级别定义专属透传信号 (参数：指令str, 显示标志list, 动作编号int)
    Drv_TxSignal_flag = pyqtSignal(str, list, int)


    def __init__(self, controller):
        super().__init__()
        
        self.ctrl = controller
        self.log_handler = setup_logger()
        
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.settings = QSettings("MyLab", "CDM_Bias_System")
        self.board_config_path = os.path.join(os.getcwd(), "data", "config_Board.ini")
        
        self.serial_config = {}
        self.stm_vref = 3.3
        self.adc_offsets = {}
        self.adc_cache = {} 
        
        self.is_power_up_check = False
        

        # --- [新增] DRV 模块专属跨端数据池 ---
        self.DRV_Rx_Array = [""]
        # 动态创建信号（利用 Qt 的特性，也可以在类顶部定义）
        if not hasattr(self.__class__, 'Drv_TxSignal_flag'):
            self.__class__.Drv_TxSignal_flag = pyqtSignal(str, list, int)
            
        self.drv_pane = DRV_Control_Pane(self.Drv_TxSignal_flag, self.DRV_Rx_Array)
        # ----------------------------------------

        # 上电检查定时器
        self.power_check_timer = QTimer()
        self.power_check_timer.setSingleShot(True)
        self.power_check_timer.timeout.connect(self._start_stm_adc_read)

        self._init_ui_state()
        self._load_board_config() 
        self._connect_signals()


        
    def _init_ui_state(self):
        self.setWindowTitle("CDM Bias Control - GUI V7.5 Optimized")
        self.ui.SerialPortA.clear()
        ports = [port.portName() for port in QSerialPortInfo.availablePorts()]
        ports.sort()
        self.ui.SerialPortA.addItems(ports)
        last_port = self.settings.value("LastSerialPort", "COM1")
        idx = self.ui.SerialPortA.findText(str(last_port))
        if idx >= 0: self.ui.SerialPortA.setCurrentIndex(idx)
        
        self._update_connect_btn_ui(False)
        
        self.ui.pushButton_PowerUp.setEnabled(True)
        self.ui.pushButton_PowerOff.setEnabled(False)

    def _load_board_config(self):
        if not os.path.exists(self.board_config_path):
            log.warning(f"Config not found: {self.board_config_path}")
            return

        conf = QSettings(self.board_config_path, QSettings.IniFormat)
        conf.beginGroup("setup_SerialPort")
        self.serial_config = {
            'port': conf.value("SerialPort_COM", "COM1"),
            'baud': conf.value("SerialPort_Baud", 115200),
            'data_bits': conf.value("SerialPort_DataBit", 8),
            'parity': conf.value("SerialPort_Parity", "None"),
            'stop_bits': conf.value("SerialPort_StopBit", 1),
            'flow': conf.value("SerialPort_Flow", "None")
        }
        conf.endGroup()
        
        conf.beginGroup("setup_PowerControl")
        vref = conf.value("STM32_ADC_VREF")
        if vref: self.stm_vref = float(vref)
        
        self.adc_offsets['DRV_VCC'] = float(conf.value("AdOffset_DRV_VCC", 0))
        self.adc_offsets['DRV_VDR'] = float(conf.value("AdOffset_DRV_VDR", 0))
        self.adc_offsets['HeaterVCC'] = float(conf.value("AdOffset_HeaterVCC", 0))

        def set_ui(key, w):
            v = conf.value(key)
            if v: w.setText(str(v))

        set_ui("TargetVolt_HeaterVCC", self.ui.TargetVolt_HeaterVCC)
        set_ui("TargetVolt_DRV_VCC", self.ui.TargetVolt_DRV_VCC)
        set_ui("TargetVolt_DRV_VDR", self.ui.TargetVolt_DRV_VDR)
        
        set_ui("DaVolt_Adjust_HeaterVCC", self.ui.DaVolt_Adjust_HeaterVCC)
        set_ui("DaVolt_Adjust_DRV_VCC", self.ui.DaVolt_Adjust_DRV_VCC)
        set_ui("DaVolt_Adjust_DRV_VDR", self.ui.DaVolt_Adjust_DRV_VDR)
        
        conf.endGroup()

    def _save_serial_port_config(self, port_name):
        conf = QSettings(self.board_config_path, QSettings.IniFormat)
        conf.beginGroup("setup_SerialPort")
        conf.setValue("SerialPort_COM", port_name)
        conf.endGroup()
        conf.sync()

    def _connect_signals(self):
        self.ui.SerialPortA_OnOff.clicked.connect(self._on_btn_connect_clicked)
        self.ui.SerialPortA_Sent.clicked.connect(self._on_btn_manual_send)
        if hasattr(self.ui, 'SerialPortA_textEdit'):
            self.ui.SerialPortA_textEdit.returnPressed.connect(self._on_btn_manual_send)

        self.ui.pushButton_PowerUp.clicked.connect(self._on_btn_power_up)
        self.ui.pushButton_PowerOff.clicked.connect(self._on_btn_power_off)
        
        self.ui.Rd_AllADC.clicked.connect(self._on_btn_read_all_adc)
        if hasattr(self.ui, 'QTextBrowser_Clear_Info'):
            self.ui.QTextBrowser_Clear_Info.clicked.connect(self._on_btn_clear_info)

        # DAC 设置
        self.ui.WrtDA_HeaterVCC.clicked.connect(lambda: self._send_voltage_to_dac(1, self.ui.DaVolt_Adjust_HeaterVCC))
        self.ui.WrtDA_DRV_VCC.clicked.connect(lambda: self._send_voltage_to_dac(2, self.ui.DaVolt_Adjust_DRV_VCC))
        self.ui.WrtDA_DRV_VDR.clicked.connect(lambda: self._send_voltage_to_dac(3, self.ui.DaVolt_Adjust_DRV_VDR))

        # DAC 读取
        if hasattr(self.ui, 'ReadDA_HeaterVCC'):
            self.ui.ReadDA_HeaterVCC.clicked.connect(lambda: self._on_btn_read_dac(1))
        if hasattr(self.ui, 'ReadDA_DRV_VCC'):
            self.ui.ReadDA_DRV_VCC.clicked.connect(lambda: self._on_btn_read_dac(2))
        if hasattr(self.ui, 'ReadDA_DRV_VDR'):
            self.ui.ReadDA_DRV_VDR.clicked.connect(lambda: self._on_btn_read_dac(3))

        # 更新功耗报告
        self.ui.Update_PwrReport.clicked.connect(self._on_btn_pwr_report)
        if hasattr(self.ui, 'CDM_Consumption_Update'):
             self.ui.CDM_Consumption_Update.clicked.connect(self._on_btn_pwr_report)

        # 信号连接
        self.log_handler.sig_log.connect(self._handle_log_msg)
        self.ctrl.sig_conn_status.connect(self._on_driver_status)
        self.ctrl.sig_stm_power_data.connect(self._on_stm_power_update)

        self.ctrl.sig_stm_dac_read.connect(self._on_stm_dac_read)
        self.ctrl.sig_stm_info.connect(self._handle_log_msg)

        # === 1. Find Point 扫点控制与复选框互斥绑定 ===
        if hasattr(self.ui, 'FindPoint'):
            self.ui.FindPoint.clicked.connect(self._on_btn_find_point)
            
        # 兼容不同版本的 UI 命名 (当前 Ui_main_window.py 中名为 Lock_Max_EN 和 Lock_MIN_EN)
        self.cb_max = getattr(self.ui, 'Lock_Max_EN', getattr(self.ui, 'Lock_All_Max_EN', None))
        self.cb_nnq = getattr(self.ui, 'Lock_MIN_EN', getattr(self.ui, 'Lock_NNQ_EN', None))
        
        # 实现勾选互斥：勾选A则取消B
        if self.cb_max and self.cb_nnq:
            self.cb_max.toggled.connect(lambda checked: self.cb_nnq.setChecked(False) if checked else None)
            self.cb_nnq.toggled.connect(lambda checked: self.cb_max.setChecked(False) if checked else None)

        # === 2. Dither 批量读写绑定 ===
        # 严格按照您提供的命名格式。Rd 按钮带有双下划线如 LockDither__XI_Rd
        self.dither_ui_map = {
            "XI":   (getattr(self.ui, 'LockDither_XI', None),   getattr(self.ui, 'LockDither_XI_Set', None),   getattr(self.ui, 'LockDither_XI_Rd', None)),
            "XQ":   (getattr(self.ui, 'LockDither_XQ', None),   getattr(self.ui, 'LockDither_XQ_Set', None),   getattr(self.ui, 'LockDither_XQ_Rd', None)),
            "YI":   (getattr(self.ui, 'LockDither_YI', None),   getattr(self.ui, 'LockDither_YI_Set', None),   getattr(self.ui, 'LockDither_YI_Rd', None)),
            "YQ":   (getattr(self.ui, 'LockDither_YQ', None),   getattr(self.ui, 'LockDither_YQ_Set', None),   getattr(self.ui, 'LockDither_YQ_Rd', None)),
            "XP_I": (getattr(self.ui, 'LockDither_XP_I', None), getattr(self.ui, 'LockDither_XP_I_Set', None), getattr(self.ui, 'LockDither_XP_I_Rd', None)),
            "XP_Q": (getattr(self.ui, 'LockDither_XP_Q', None), getattr(self.ui, 'LockDither_XP_Q_Set', None), getattr(self.ui, 'LockDither_XP_Q_Rd', None)),
            "YP_I": (getattr(self.ui, 'LockDither_YP_I', None), getattr(self.ui, 'LockDither_YP_I_Set', None), getattr(self.ui, 'LockDither_YP_I_Rd', None)),
            "YP_Q": (getattr(self.ui, 'LockDither_YP_Q', None), getattr(self.ui, 'LockDither_YP_Q_Set', None), getattr(self.ui, 'LockDither_YP_Q_Rd', None)),
        }
        # 动态绑定槽函数
        for ch_name, (le, btn_wr, btn_rd) in self.dither_ui_map.items():
            if btn_wr and le:
                btn_wr.clicked.connect(lambda checked, ch=ch_name, line_edit=le: self._write_dither(ch, line_edit))
            if btn_rd:
                btn_rd.clicked.connect(lambda checked, ch=ch_name: self._read_dither(ch))
        # 接收底层 Dither 数据返回更新 UI
        self.ctrl.sig_dither_read.connect(self._on_dither_read_update)


        # === 3. 大阵列截获与图表触发绑定 ===
        self.pending_action = ""  # 记录当前触发的是 FFT 还是 NOISE 等
        
        if hasattr(self.ui, 'Rd_P22'):
            self.ui.Rd_P22.clicked.connect(lambda: self._trigger_bulk_read('P22_RAW'))
        if hasattr(self.ui, 'FFT_Analysis'):
            self.ui.FFT_Analysis.clicked.connect(lambda: self._trigger_bulk_read('FFT'))
        if hasattr(self.ui, 'Nosie_Analysis'):
            self.ui.Nosie_Analysis.clicked.connect(lambda: self._trigger_bulk_read('NOISE'))
            
        if hasattr(self.ui, 'All_Max_ScanResult'):
            self.ui.All_Max_ScanResult.clicked.connect(lambda: self._trigger_scan_read(False))
        if hasattr(self.ui, 'NNQ_ScanResult'):
            self.ui.NNQ_ScanResult.clicked.connect(lambda: self._trigger_scan_read(True))

        # 挂载底层状态机拦截到大数据的回调信号
        self.ctrl.sig_bulk_data_ready.connect(self._on_bulk_data_ready)
        
        # 用于保持子窗口引用的列表，防止被 Python 垃圾回收销毁
        self.plot_windows = []


        # ==========================================================
        # [新增] DRV 模块的信号桥接 (Tx发 / Rx收 / 面板呼出)
        # ==========================================================
        # 1. 呼出面板 (假设你主界面按钮叫 pushButton_DRV_Control，若名字不同请替换)
        if hasattr(self.ui, 'pushButton_DRV_Control'):
            self.ui.pushButton_DRV_Control.clicked.connect(self.drv_pane.show)
            
        # 2. Tx 发送路由绑定
        self.Drv_TxSignal_flag.connect(self.route_drv_tx_to_serial)
        
        # 3. Rx 接收路由绑定（复用 controller 抛出的信息流）
        # 确保全局的信息流 (包含 ACK 和 RAW) 都会流经 DRV 的拦截器
        self.ctrl.sig_stm_info.connect(self._on_drv_data_received)
        # 建议额外绑定 sig_stm_ack，防止部分格式标准的回复只走了 ACK 信号不走 info 信号
        self.ctrl.sig_stm_ack.connect(self._on_drv_data_received)


    def _update_connect_btn_ui(self, is_connected):
        if is_connected:
            self.ui.SerialPortA_OnOff.setText("断开/Disconnect")
            self.ui.SerialPortA_OnOff.setStyleSheet("background-color: #4CAF50; color: white;")
            self.ui.SerialPortA.setEnabled(False) 
        else:
            self.ui.SerialPortA_OnOff.setText("连接/Connect")
            self.ui.SerialPortA_OnOff.setStyleSheet("") 
            self.ui.SerialPortA.setEnabled(True)

    # --- 逻辑功能函数 ---

    def _on_btn_read_all_adc(self):
        log.info("Requesting ALL ADC Data (STM:ADC ALL)...")
        self.ctrl.send_cmd(CmdType.STM_READ_ALL_ADC, wait_for_ack=False)

    def _on_btn_read_dac(self, ch):
        log.info(f"Reading DAC Channel {ch}...")
        self.ctrl.send_cmd(CmdType.STM_READ_DAC, ch, wait_for_ack=False)

    def _send_voltage_to_dac(self, ch, line_edit):
        try:
            text = line_edit.text().strip()
            if not text: return
            volt = float(text)
            dac_code = int((volt / DAC_REF_VOLT) * DAC_RESOLUTION)
            dac_code = max(0, min(DAC_RESOLUTION, dac_code))
            
            self.ctrl.send_cmd(CmdType.STM_SET_DAC, ch, dac_code, wait_for_ack=False)
            log.info(f"Set STM DAC Ch{ch}: {volt:.3f}V -> Code {dac_code}")
        except ValueError:
            QMessageBox.warning(self, "格式错误", "请输入有效的电压数值")

    def _calculate_stm_value(self, ch_idx, raw_adc):
        val = 0.0
        # 1: DRV_VCC, 2: DRV_VDR, 5: Heater
        if ch_idx in [1, 2, 5]: 
            val = (raw_adc / 4096.0) * self.stm_vref * 3.0
        # 3: ICC, 4: IDD
        elif ch_idx in [3, 4]: 
            val = (raw_adc / 4096.0) * self.stm_vref / 200.0 * 300 / 50 / 0.1 * 1000
        elif ch_idx == 6: 
            val = (raw_adc / 4096.0) * self.stm_vref * 3.0 - 5.039
        return float(val)

    def _update_single_power_ui_field(self, key, raw_val):
        """[新增] 仅更新单个UI值，不进行功耗计算"""
        # 映射 Key 到计算逻辑
        if key == 'ADC_HEATER_VCC':
            val = self._calculate_stm_value(5, raw_val)
            val = max(0, val - self.adc_offsets.get('HeaterVCC', 0))
            self.ui.AdtoVolt_HeaterVCC.setText(f"{val:.3f}")
            
        elif key == 'ADC_DRV_VCC':
            val = self._calculate_stm_value(1, raw_val)
            val = max(0, val - self.adc_offsets.get('DRV_VCC', 0))
            self.ui.AdtoVolt_DRV_VCC.setText(f"{val:.3f}")
            
        elif key == 'ADC_DRV_VDD': # VDR
            val = self._calculate_stm_value(2, raw_val)
            val = max(0, val - self.adc_offsets.get('DRV_VDR', 0))
            self.ui.AdtoVolt_DRV_VDR.setText(f"{val:.3f}")
            
        elif key == 'ADC_DRV_ICC':
            val = self._calculate_stm_value(3, raw_val)
            self.ui.DRV_ICC.setText(f"{val:.1f}")
            
        elif key == 'ADC_DRV_IDD':
            val = self._calculate_stm_value(4, raw_val)
            self.ui.DRV_IDD.setText(f"{val:.1f}")

    # --- Slot 回调 ---

    @pyqtSlot()
    def _on_btn_clear_info(self):
        """[新增] 清空日志显示框"""
        if hasattr(self.ui, 'QTextBrowser_Print'):
            self.ui.QTextBrowser_Print.clear()
            # 可选：清空后打印一条提示，确认操作有效
            # log.info("=== Log Cleared ===")


    @pyqtSlot()
    def _on_btn_power_up(self):
        log.info("=== 开始上电流程 ===")
        self.is_power_up_check = True


        self._send_voltage_to_dac(1, self.ui.DaVolt_Adjust_HeaterVCC)
        self._send_voltage_to_dac(2, self.ui.DaVolt_Adjust_DRV_VCC)
        self._send_voltage_to_dac(3, self.ui.DaVolt_Adjust_DRV_VDR)


        self.ctrl.send_cmd(CmdType.STM_POWER_ON, wait_for_ack=False)
        log.info("等待电源稳定 (1s)...")
        self.power_check_timer.start(1000)
        
    @pyqtSlot()
    def _on_btn_pwr_report(self):
        log.info("\n")
        log.info("更新功耗报告 (Requesting Power ADC)...")
        self._start_stm_adc_read()

    def _start_stm_adc_read(self):
        self.adc_cache.clear()
        self.ctrl.send_cmd(CmdType.STM_READ_POWER, wait_for_ack=False)

    @pyqtSlot(dict)
    def _on_stm_power_update(self, data_dict):
        """
        [优化] 收到 ADC 数据包，根据数据量决定处理方式
        """
        
        
        self.adc_cache.update(data_dict)
        count = len(data_dict)
        
        # 情况1: 数据量 > 15 -> STM:ADC ALL
        # 仅已在 Controller 中 Log 显示，此处不进行功耗计算，避免刷屏
        if count > 15:
            return

        # 情况2: 数据量 1~2 -> 单通道读取 (如 ADC 1)
        # 更新对应的UI显示，但不计算总功耗
        if count < 3:
            for key, val in data_dict.items():
                self._update_single_power_ui_field(key, val)
            return

        # 情况3: 数据量 3~10 -> STM:ADC power (功耗报告)
        # 只有这种情况才执行完整的校验和功耗计算
        required_keys = ['ADC_HEATER_VCC', 'ADC_DRV_VCC', 'ADC_DRV_VDD', 'ADC_DRV_ICC', 'ADC_DRV_IDD']
        
        if self.is_power_up_check:
            # 上电检查必须严格等待所有key
            if all(k in self.adc_cache for k in required_keys):
                self._verify_power_stm()
        else:
            # 手动更新，只要看起来像 Power 包就刷新
            if any(k in self.adc_cache for k in required_keys):
                self._verify_power_stm()

    def _verify_power_stm(self):
        """计算并显示 5 个电源值及功耗 (仅在 Power Report 时调用)"""
        # 1. 获取 Raw 值
        raw_heater = self.adc_cache.get('ADC_HEATER_VCC', 0)
        raw_vcc    = self.adc_cache.get('ADC_DRV_VCC', 0)
        raw_vdr    = self.adc_cache.get('ADC_DRV_VDD', 0) 
        raw_icc    = self.adc_cache.get('ADC_DRV_ICC', 0)
        raw_idd    = self.adc_cache.get('ADC_DRV_IDD', 0)

        # 2. 转换物理值
        val_heater = self._calculate_stm_value(5, raw_heater)
        val_vcc    = self._calculate_stm_value(1, raw_vcc)
        val_vdr    = self._calculate_stm_value(2, raw_vdr)
        val_icc    = self._calculate_stm_value(3, raw_icc) # mA
        val_idd    = self._calculate_stm_value(4, raw_idd) # mA

        # 3. 应用 Offset
        val_heater = max(0, val_heater - self.adc_offsets.get('HeaterVCC', 0))
        val_vcc    = max(0, val_vcc    - self.adc_offsets.get('DRV_VCC', 0))
        val_vdr    = max(0, val_vdr    - self.adc_offsets.get('DRV_VDR', 0))

        # 4. 刷新 UI
        self.ui.AdtoVolt_HeaterVCC.setText(f"{val_heater:.3f}")
        self.ui.AdtoVolt_DRV_VCC.setText(f"{val_vcc:.3f}")
        self.ui.AdtoVolt_DRV_VDR.setText(f"{val_vdr:.3f}")
        self.ui.DRV_ICC.setText(f"{val_icc:.1f}")
        self.ui.DRV_IDD.setText(f"{val_idd:.1f}")

        # 5. 计算功耗
        pwr_drv = (val_vcc * val_icc + val_vdr * val_idd) / 1000.0
        
        log.info(f"Power Calc: {pwr_drv:.3f}W (VCC:{val_vcc:.2f}V, VDR:{val_vdr:.2f}V)")
        if hasattr(self.ui, 'CDM_Consumption'):
            self.ui.CDM_Consumption.setText(f"{pwr_drv:.3f}")

        # 6. 上电检查逻辑
        if self.is_power_up_check:
            self.is_power_up_check = False 
            self._check_voltage_targets(val_heater, val_vcc, val_vdr, pwr_drv)

    def _check_voltage_targets(self, val_heater, val_vcc, val_vdr, pwr_drv):
        target_heater = float(self.ui.TargetVolt_HeaterVCC.text() or 0)
        target_vcc    = float(self.ui.TargetVolt_DRV_VCC.text() or 0)
        target_vdr    = float(self.ui.TargetVolt_DRV_VDR.text() or 0)

        check_msg = []
        is_ok = True

        def check(name, target, real):
            nonlocal is_ok
            if target == 0: 
                check_msg.append(f"{name}: {real:.3f}V (Skip)")
                return True
            if target <= real <= (target + 0.25): 
                check_msg.append(f"{name}: OK ({real:.3f}V)")
                return True
            else:
                check_msg.append(f"{name}: FAIL ({real:.3f}V, Exp {target})")
                is_ok = False
                return False

        check("Heater", target_heater, val_heater)
        check("DRV_VCC", target_vcc,    val_vcc)
        check("DRV_VDR", target_vdr,    val_vdr)

        if is_ok:
            log.info("\n\n>>> 上电成功/Power-on succeed <<<\n")
            self.ui.pushButton_PowerUp.setEnabled(False)
            self.ui.pushButton_PowerOff.setEnabled(True)
        else:

            log.error("\n\n>>> 上电异常/Power-on error <<<\n")
            self._on_btn_power_off()
            # QMessageBox.critical(self, "异常", f"电压异常:\n\n{chr(10).join(check_msg)}")

    @pyqtSlot(int, int)
    def _on_stm_dac_read(self, ch, dac_val):
        volt = (dac_val / DAC_RESOLUTION) * DAC_REF_VOLT
        log.info(f"Read DAC Ch{ch}: Code {dac_val} -> {volt:.2f}V")
        
        widget_map = {
            1: self.ui.DaVolt_Adjust_HeaterVCC,
            2: self.ui.DaVolt_Adjust_DRV_VCC,
            3: self.ui.DaVolt_Adjust_DRV_VDR
        }
        
        # if ch in widget_map:
        #     widget_map[ch].setText(f"{volt:.1f}")

        widget_map[ch].setText(f"{volt:.2f}")

    @pyqtSlot()
    def _on_btn_power_off(self):
        log.info("执行下电...")
        self.is_power_up_check = False 
        self.ctrl.send_cmd(CmdType.STM_POWER_OFF, wait_for_ack=False)
        self.ui.pushButton_PowerUp.setEnabled(True)
        self.ui.pushButton_PowerOff.setEnabled(False)
        self.ui.AdtoVolt_HeaterVCC.clear()
        self.ui.AdtoVolt_DRV_VCC.clear()
        self.ui.AdtoVolt_DRV_VDR.clear()
        self.ui.DRV_ICC.clear()
        self.ui.DRV_IDD.clear()
        if hasattr(self.ui, 'CDM_Consumption'):
            self.ui.CDM_Consumption.clear()

    @pyqtSlot()
    def _on_btn_connect_clicked(self):
        if "连接" in self.ui.SerialPortA_OnOff.text() or "Connect" in self.ui.SerialPortA_OnOff.text():
            port_name = self.ui.SerialPortA.currentText()
            if not port_name: return
            conn_settings = self.serial_config.copy()
            conn_settings['port'] = port_name
            self._save_serial_port_config(port_name)
            self.ctrl.open_device(port_name, conn_settings)
        else:
            self.ctrl.close_device()

    @pyqtSlot(int, str)
    def _on_driver_status(self, status, msg):

        self._update_connect_btn_ui(status == 1)

        # ==========================================
        # 【新增同步】：将底层的物理连接状态，实时同步给 DRV 面板的状态锁
        if hasattr(self, 'drv_pane'):
            self.drv_pane.is_serial_connected = (status == 1)
        # ==========================================

        if status == 0 and "Error" in msg:
            QMessageBox.warning(self, "连接错误", msg)

    @pyqtSlot()
    def _on_btn_manual_send(self):
        if not hasattr(self.ui, 'SerialPortA_textEdit'): return
        text = self.ui.SerialPortA_textEdit.text().strip()
        if not text: return
        self.ctrl.send_cmd(CmdType.CMD_RAW, text, wait_for_ack=False)


    # ------------------- 主界面日志隔离与接收咽喉 -------------------
    @pyqtSlot(str)
    def _handle_log_msg(self, msg):
        """
        【日志防线】：屏蔽 DRV 相关的通信日志在主界面打印，
        但由于 logger 机制，后台的 .log 文件依然会忠实记录一切。
        """
        # 如果包含 DRV 的专属指令头 MAOM，直接拦截，不上屏
        if "MAOM" in msg:
            return 
            
        log_widget = getattr(self.ui, 'QTextBrowser_Print', None)
        if log_widget:
            log_widget.append(msg)
            cursor = log_widget.textCursor()
            cursor.movePosition(cursor.End)
            log_widget.setTextCursor(cursor)


    @pyqtSlot()
    def _on_btn_find_point(self):
        """解析 CheckBox 发送对应找点指令"""
        mode = "MAX"  # 默认兜底
        
        # 优先判断 NNQ 是否勾选
        if hasattr(self, 'cb_nnq') and self.cb_nnq and self.cb_nnq.isChecked():
            mode = "NNQ"
        elif hasattr(self, 'cb_max') and self.cb_max and self.cb_max.isChecked():
            mode = "MAX"
        else:
            QMessageBox.warning(self, "操作提示", "请先勾选找点模式 (MAX 或 NNQ)！")
            return
            
        log.info(f"Triggering Find Point Mode: {mode}")
        self.ctrl.send_cmd(CmdType.START_SCAN, mode, wait_for_ack=False)

    def _write_dither(self, ch_name, line_edit):
        """异步下发写入微扰"""
        text = line_edit.text().strip()
        if not text: return
        try:
            val = int(text)
            self.ctrl.send_cmd(CmdType.SET_DITHER, ch_name, val, wait_for_ack=False)
            log.info(f"Write Dither {ch_name}: {val} mV")
        except ValueError:
            QMessageBox.warning(self, "格式错误", f"{ch_name} 微扰必须为整数！")

    def _read_dither(self, ch_name):
        """异步发送读取请求"""
        self.ctrl.send_cmd(CmdType.GET_DITHER, ch_name, wait_for_ack=False)
        log.info(f"Request Read Dither {ch_name} ...")

    @pyqtSlot(str, int)
    def _on_dither_read_update(self, ch_name, val):
        """接收下位机 Resp 并更新 UI"""
        if ch_name in self.dither_ui_map:
            line_edit = self.dither_ui_map[ch_name][0]
            if line_edit:
                line_edit.setText(str(val))

    def _trigger_bulk_read(self, action_type):
        self.pending_action = action_type
        if action_type == 'NOISE':
            self.ctrl.send_cmd(CmdType.GET_PD_ADC_NOISE, wait_for_ack=False)
            log.info("Requesting 4320-point Pure DC Data for Noise Analysis...")
        else:
            self.ctrl.send_cmd(CmdType.GET_P22_DATA, 1440, wait_for_ack=False)
            log.info("Requesting 1440-point P22 Data...")

    def _trigger_scan_read(self, is_nnq):
        if is_nnq:
            self.ctrl.send_cmd(CmdType.EXPORT_NNQ_DATA, wait_for_ack=False)
            log.info("Requesting 6-Channel NNQ Data...")
        else:
            # 循环请求6个通道的 SCAN_CURVE
            for ch in range(1, 7):
                self.ctrl.send_cmd(CmdType.EXPORT_SCAN_CURVE, ch, wait_for_ack=False)
            log.info("Requesting 6-Channel MAX Scan Data...")

    @pyqtSlot(str, object)
    def _on_bulk_data_ready(self, data_type, payload):
        """当底层吃满一整块数组或字典时，在此触发落盘与绘图"""
        log.info(f"Bulk Data [{data_type}] Received! Processing...")
        
        # 1. ==== 异步文件落盘系统 ====
        if hasattr(self.ui, 'En_AutoSave_TxT') and self.ui.En_AutoSave_TxT.isChecked():
            os.makedirs("data/analysis", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/analysis/{data_type}_{timestamp}.txt"
            
            try:
                if data_type == "P22":
                    np.savetxt(filename, payload, fmt="%.6f")
                else: # NNQ 或是 SCAN (这是个字典)
                    with open(filename, 'w') as f:
                        for ch, arr in payload.items():
                            f.write(f"----BEGIN_{data_type}_{ch}----\n")
                            # [新增] 兼容 2D 数据的格式化保存
                            if data_type == "NNQ":
                                np.savetxt(f, arr, fmt="%d, %.6f") # 第一列DA存为整型
                            else:
                                np.savetxt(f, arr, fmt="%.6f")
                            f.write(f"----END_{data_type}----\n")
                log.info(f"Data Auto Saved to {filename}")
            except Exception as e:
                log.error(f"Auto Saved failed: {e}")
                
        # 2. ==== PyQtGraph 子窗口绘图调度 ====
        win = None
        if data_type == "P22":
            if self.pending_action == 'FFT':
                win = FFTPlotWindow(payload, fs=19200.0, is_noise=False)
            elif self.pending_action == 'NOISE':
                win = FFTPlotWindow(payload, fs=19200.0, is_noise=True)
            else: # P22_RAW 仅读取不画图
                pass 
                
        elif data_type in ("NNQ", "SCAN"):
            title = "NNQ 2D+1D Scan" if data_type == "NNQ" else "All Max Scan"
            win = GridPlotWindow(payload, title_prefix=title)

        # 弹出独立的无阻塞图表窗口，并确保存活
        if win:
            self.plot_windows.append(win)
            win.show()
            
            # [附加] 如果勾选了保存TXT，顺便把这张高清图表也截图保存
            if hasattr(self.ui, 'En_AutoSave_TxT') and self.ui.En_AutoSave_TxT.isChecked():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                img_path = f"data/analysis/{data_type}_Plot_{timestamp}.png"
                # PyQtGraph 原生截图
                win.grab().save(img_path)          


    def show_drv_pane(self):
        """唤醒 DRV 子窗口"""
        self.drv_pane.show()

    # ------------------- DRV 跨端通信路由 -------------------
    @pyqtSlot(str, list, int)
    def route_drv_tx_to_serial(self, DA_cmd, show_flag, action_num):
        """
        【发送咽喉】：将 DRV 模块的指令打上路由前缀并压入队列
        """
        # 核心防线：为底层协议网关强制打上 STM: 路由标签
        # DA_cmd 例如 'MAOM 0 0200'，打包后变为 'STM:MAOM 0 0200'
        routed_cmd = f"STM:{DA_cmd}"
        
        if self.ctrl:
            self.ctrl.send_cmd(CmdType.CMD_RAW, routed_cmd, wait_for_ack=False)
            # 维持 UI 状态，注意这里返回给界面的依然是原始指令 DA_cmd
            self.drv_pane.Drv_TxFinish_flag.emit(DA_cmd, True, show_flag)

    @pyqtSlot(str)
    def _on_drv_data_received(self, msg):
        """
        【拦截器升级】：精准识别 READ 与 WRITE 报文，防止数据串包
        """
        if "MAOM" in msg and "0x" in msg:
            try:
                # 物理切片：提取最后一个 0x 后面的数据
                hex_val = msg.split("0x")[-1].strip()
                self.DRV_Rx_Array[0] = hex_val
                
                # --- 核心逻辑分流 ---
                if "READ" in msg.upper():
                    # 只有 READ 报文的回复，才允许触发子界面的数据回填
                    self.drv_pane.Drv_TxFinish_flag.emit(f"DRV Read:{hex_val}", True, self.drv_pane.print_info_Rd)
                else:
                    # 对于 WRITE 或其他确认包，原样发送，用于清理 TxFinish_Check 的状态
                    self.drv_pane.Drv_TxFinish_flag.emit(msg, True, self.drv_pane.print_info_Wrt)
            except Exception:
                pass


    def closeEvent(self, event):
        """全局热退出防护"""
        # 关闭 DRV 子界面
        if hasattr(self, 'drv_pane') and self.drv_pane.isVisible():
            self.drv_pane.close()
        
        # 停止底层的 serial_worker 线程...
        if hasattr(self, 'serial_worker'):
            self.serial_worker.stop()
            
        event.accept()