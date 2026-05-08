from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import pyqtSignal, Qt
import sys, os, datetime
from time import sleep

sys.path.append(os.getcwd())
from utils.Ui_DRV_Control import Ui_Form

class DRV_Control_Pane(QtWidgets.QWidget, Ui_Form):

    Drv_TxFinish_flag = pyqtSignal(str, bool, list)  # DRV Tx完成，传递回来标志位
    Drv_RxData_Reback = pyqtSignal(int, int, list)
    Drv_window_Close = pyqtSignal()

    def __init__(self, Drv_TxSignal_flag, DRV_Rx_Array):
        super().__init__()
        self.setupUi(self)
        
        self.setWindowFlag(Qt.WindowCloseButtonHint)
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.move(200, 200)
        # self.resize(1200, 660)
        
        # 通信总线与缓存挂载
        self.Drv_TxSignal = Drv_TxSignal_flag 
        self.Rx_Array = DRV_Rx_Array
        
        self.ActionNum_0 = 0
        self.print_info_all = [1, True, True]
        self.print_info_Wrt = [1, False, False]
        self.print_info_Rd  = [1, False, True]
        self.print_info_no  = [1, False, False]

        self.DRV_Vendor_Flag = ''
        self.is_serial_connected = False  # 【新增】：跨端同步的串口状态锁
        
        # 配置文件加载
        self.setting = QtCore.QSettings("./data/config_Board.ini", QtCore.QSettings.IniFormat)
        self.setting.setIniCodec("UTF-8")
        self.setting_CDM = QtCore.QSettings("./data/config_CDM.ini", QtCore.QSettings.IniFormat)
        self.setting_CDM.setIniCodec("UTF-8")
        
        # 信号槽绑定
        self.Drv_TxFinish_flag.connect(self.Drv_TxFinish_Check)
        self.DRV_INFO_Read.clicked.connect(lambda: self.DRV_INFO_Read_cb(self.print_info_Rd))
        self.DRV_Reg_Wrt.clicked.connect(lambda: self.DRV_Reg_Wrt_cb(self.print_info_no))
        self.DRV_Reg_Rd.clicked.connect(lambda: self.DRV_Reg_Rd_cb(self.print_info_Wrt))

        # VG 读写绑定
        self.DRV_VG_Rd.clicked.connect(lambda: self.DRV_VGRead_cb(self.print_info_Rd))
        self.DRV_VG0_Wrt.clicked.connect(lambda: self.DRV_VGWrite_cb(0, self.print_info_no))
        self.DRV_VG1_Wrt.clicked.connect(lambda: self.DRV_VGWrite_cb(1, self.print_info_no))
        self.DRV_VG2_Wrt.clicked.connect(lambda: self.DRV_VGWrite_cb(2, self.print_info_no))
        self.DRV_VG3_Wrt.clicked.connect(lambda: self.DRV_VGWrite_cb(3, self.print_info_no))

        # PKD 读绑定
        self.DRV_PKD_Rd.clicked.connect(lambda: self.DRV_PKDRead_cb(self.print_info_Rd))

        # PEAKING 读写绑定
        self.DRV_Peaking_Rd.clicked.connect(lambda: self.DRV_PeakingRead_cb(self.print_info_Rd))
        self.DRV_Peaking_Wrt_0.clicked.connect(lambda: self.DRV_PeakingWrite_cb(0, self.print_info_no))
        self.DRV_Peaking_Wrt_1.clicked.connect(lambda: self.DRV_PeakingWrite_cb(1, self.print_info_no))
        self.DRV_Peaking_Wrt_2.clicked.connect(lambda: self.DRV_PeakingWrite_cb(2, self.print_info_no))
        self.DRV_Peaking_Wrt_3.clicked.connect(lambda: self.DRV_PeakingWrite_cb(3, self.print_info_no))        

        # VDCOUT / 控制模式 / 增益模式 / 温度读取
        self.DRV_VDCOUT_Rd.clicked.connect(lambda: self.DRV_VDCOUT_Read_cb(self.print_info_Rd))
        self.ControlMode_Rd.clicked.connect(lambda: self.DRV_ControlMode_Read_cb(self.print_info_Rd))
        self.GainMode_Rd.clicked.connect(lambda: self.DRV_GainMode_Read_cb(self.print_info_Rd))
        self.GainMode_Wrt.clicked.connect(lambda: self.DRV_GainMode_Write_cb(self.print_info_Rd))
        self.DRV_Temperature_Rd.clicked.connect(lambda: self.DRV_TemperatureRead_cb(self.print_info_Rd))
        
        self.Save_Conv_Volt_Param.clicked.connect(self.DRV_Convert_Volt_Parameter)

    # ------------------- 核心原子防御与底层机制 -------------------
    
    def _hardware_throttle(self):
        """【硬件保护防线】连续下发多条指令时的节流阀，防止打爆 STM32 UART 16-byte FIFO"""
        sleep(0.02)
        QtWidgets.QApplication.processEvents()
        
    def _format_hex_safe(self, text, length=4):
        """【越界防御】强制将用户输入转换为标准大写十六进制字符串，拦截非法字符"""
        if not text:
            return False, ""
        try:
            val = int(text, 16)
            format_str = f"{{:0{length}X}}"
            return True, format_str.format(val)
        except ValueError:
            return False, ""

    def Check_RegValue(self, msg='The Value cannot be empty or invalid!'):
        """统一错误拦截提示"""
        QtWidgets.QMessageBox.warning(self, "错误提示", msg, QMessageBox.Ok | QMessageBox.Close)

    def _check_vendor_ready(self):
        """校验是否已读取 DRV 信息锁定厂家"""
        if not (self.VendorID_M_EN.isChecked() or self.VendorID_R_EN.isChecked()):
            QtWidgets.QMessageBox.information(self, "提示", '请先读取一次DRV_INFO,完成DRV型号确认', QMessageBox.Ok)
            return False
        return True

    # ------------------- 基础 GUI 行为 -------------------

    def closeEvent(self, a0):
        self.Drv_window_Close.emit()
        
        # 在窗口即将关闭/隐藏前，强行清空残留数据，恢复出厂状态
        self._reset_ui_state()
        
        return super().closeEvent(a0)

    def _reset_ui_state(self):
        """【UI 防线】：彻底清空历史日志、文本框数据，并重置厂家锁定状态"""
        # 1. 清空主日志大屏
        self.textBrowser_DRVControl.clear()
        
        # 2. 拔除厂家识别锁，恢复默认颜色与未勾选状态
        self.DRV_Vendor_Flag = ''
        self.VendorID_M_EN.setChecked(False)
        self.VendorID_R_EN.setChecked(False)
        self.VendorID_M_EN.setStyleSheet('background-color:rgb(255, 255, 255)')
        self.VendorID_R_EN.setStyleSheet('background-color:rgb(255, 255, 255)')
        
        # 3. 清空基础信息与环境参数
        self.VendorID_text.clear()
        self.PartID_text.clear()
        self.Version_text.clear()
        self.ControlMode_text.clear()
        self.GainMode_text.clear()
        self.DRV_Temperature.clear()
        
        # 4. 清空单个寄存器读写区
        self.DRV_Ch.clear()
        self.DRV_Reg.clear()
        self.DRV_Reg_Value.clear()
        
        # 5. 循环清空四个核心通道的大阵列数据 (利用反射机制精准定点清理)
        for ch in range(4):
            getattr(self, f"DRV_VG{ch}").clear()
            getattr(self, f"DRV_PKD{ch}").clear()
            getattr(self, f"DRV_Peaking_{ch}").clear()
            getattr(self, f"DRV_CH{ch}_VDCOUTP").clear()
            getattr(self, f"DRV_CH{ch}_VDCOUTN").clear()

            getattr(self, f"Calculate_PKD_A").clear()
            getattr(self, f"Calculate_PKD_B").clear()
            getattr(self, f"Calculate_VDCOUT_A").clear()
            getattr(self, f"Calculate_VDCOUT_B").clear()
            getattr(self, f"Calculate_Temperature_A").clear()
            getattr(self, f"Calculate_Temperature_B").clear()
            getattr(self, f"DRV_Temperature").clear()



    def Time_record(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def textBrowser_DRVControl_PrintRealTime(self, text1, flag=True):
        if flag:
            self.textBrowser_DRVControl.append(text1)
            self.cursor = self.textBrowser_DRVControl.textCursor()
            self.textBrowser_DRVControl.moveCursor(self.cursor.End)
            QtWidgets.QApplication.processEvents()

    # ------------------- 业务功能实现 -------------------

    def DRV_INFO_Read_cb(self, show_flag=[1, True, False]):
        # 【物理前置防线】：检测串口状态，无连接则直接拦截并阻断后续执行
        if not self.is_serial_connected:
            QtWidgets.QMessageBox.warning(self, "COM Connection Blocked", "Please connect COM on the main interface first!")
            return
        self.textBrowser_DRVControl_PrintRealTime(f'\nReading DRV INFO {self.Time_record()}')   

        VendorID = self.DRV_Read('MAOM 0 0200', show_flag)
        self.VendorID_text.setText(VendorID)
        self._hardware_throttle()

        PartID = self.DRV_Read('MAOM 0 0202', show_flag)
        self.PartID_text.setText(str(PartID))
        self._hardware_throttle()

        Version = self.DRV_Read('MAOM 0 0204', show_flag)
        self.Version_text.setText(str(Version))

        if self.VendorID_text.text() == '4D41':
            self.DRV_Vendor_Flag = 'M'
            self.VendorID_M_EN.setCheckable(True)
            self.VendorID_M_EN.setChecked(True)
            self.VendorID_R_EN.setChecked(False)
            self.VendorID_M_EN.setStyleSheet('background-color:rgb(0, 255, 0)')
            self.VendorID_R_EN.setStyleSheet('background-color:rgb(255, 255, 255)')
            self.DRV_M_init()
            
            self.Calculate_PKD_A.setText(self.setting.value("setup_DRV/M_Calculate_PKD_A", "1.0"))  
            self.Calculate_PKD_B.setText(self.setting.value("setup_DRV/M_Calculate_PKD_B", "0.0"))      
            self.Calculate_VDCOUT_A.setText(self.setting.value("setup_DRV/M_Calculate_VDCOUT_A", "1.0"))  
            self.Calculate_VDCOUT_B.setText(self.setting.value("setup_DRV/M_Calculate_VDCOUT_B", "0.0"))      
            self.Calculate_Temperature_A.setText(self.setting.value("setup_DRV/M_Calculate_Temperature_A", "1.0"))  
            self.Calculate_Temperature_B.setText(self.setting.value("setup_DRV/M_Calculate_Temperature_B", "0.0"))     
                
        elif self.VendorID_text.text() == 'E0CF':
            self.DRV_Vendor_Flag = 'R'
            self.VendorID_R_EN.setCheckable(True)
            self.VendorID_R_EN.setChecked(True)
            self.VendorID_M_EN.setChecked(False)
            self.VendorID_M_EN.setStyleSheet('background-color:rgb(255, 255, 255)')
            self.VendorID_R_EN.setStyleSheet('background-color:rgb(0, 255, 0)')
            
            self.Calculate_PKD_A.setText(self.setting.value("setup_DRV/R_Calculate_PKD_A", "1.0"))  
            self.Calculate_PKD_B.setText(self.setting.value("setup_DRV/R_Calculate_PKD_B", "0.0"))      
            self.Calculate_VDCOUT_A.setText(self.setting.value("setup_DRV/R_Calculate_VDCOUT_A", "1.0"))  
            self.Calculate_VDCOUT_B.setText(self.setting.value("setup_DRV/R_Calculate_VDCOUT_B", "0.0"))   
            self.Calculate_Temperature_A.setText(self.setting.value("setup_DRV/R_Calculate_Temperature_A", "1.0"))  
            self.Calculate_Temperature_B.setText(self.setting.value("setup_DRV/R_Calculate_Temperature_B", "0.0"))   
            
        self.textBrowser_DRVControl_PrintRealTime(f'DRV INFO Read Done {self.Time_record()}\n')    

    def DRV_M_init(self):
        self.textBrowser_DRVControl_PrintRealTime('\nDRV_M_4D41_Init doing...')
        self.DRV_Wrt('MAOM 0 0207 0002', self.print_info_no) # spi
        self._hardware_throttle()
        self.DRV_Wrt('MAOM 0 027A 018F', self.print_info_no)
        self._hardware_throttle()
        self.DRV_Wrt('MAOM 0 0270 0023', self.print_info_no)
        self._hardware_throttle()
        self.DRV_Wrt('MAOM 0 0272 0009', self.print_info_no)
        self._hardware_throttle()
        self.DRV_Wrt('MAOM 0 0273 00A7', self.print_info_no)
        sleep(0.5)
        self.textBrowser_DRVControl_PrintRealTime('DRV_M_4D41_Init Done\n')

    def DRV_Reg_Wrt_cb(self, show_flag=[1, True, False]):
        Ch = self.DRV_Ch.text()
        Reg = self.DRV_Reg.text()
        Reg_Value = self.DRV_Reg_Value.text()

        valid_ch, hex_ch = self._format_hex_safe(Ch, 1)
        valid_reg, hex_reg = self._format_hex_safe(Reg, 4)
        valid_val, hex_val = self._format_hex_safe(Reg_Value, 4)

        if valid_ch and valid_reg and valid_val:
            cmdText = f"MAOM {int(hex_ch, 16)} {hex_reg} {hex_val}"
            self.DRV_Wrt(cmdText, show_flag)
            self.textBrowser_DRVControl_PrintRealTime(f"Reg {hex_reg} Write {hex_val} Done\n")
        else:
            self.Check_RegValue("Channel number, register address, and Hex_Value must be valid!!")             

    def DRV_Reg_Rd_cb(self, show_flag=[1, True, False]):
        if not self._check_vendor_ready(): return
        
        Ch = self.DRV_Ch.text()
        Reg = self.DRV_Reg.text()
        valid_ch, hex_ch = self._format_hex_safe(Ch, 1)
        valid_reg, hex_reg = self._format_hex_safe(Reg, 4)

        if valid_ch and valid_reg:
            buf = self.DRV_Read(f"MAOM {int(hex_ch, 16)} {hex_reg}", show_flag)
            self.DRV_Reg_Value.setText(buf)
            self.textBrowser_DRVControl_PrintRealTime(f"{buf} \nReg {hex_reg} Read Done\n")
        else:
            self.Check_RegValue("Channel number and register address must be valid!!") 

    def DRV_VGWrite_cb(self, ch, show_flag=[1, True, False]):
        if not self._check_vendor_ready(): return
        
        vg_ui_ctrl = getattr(self, f"DRV_VG{ch}")
        valid, hex_val = self._format_hex_safe(vg_ui_ctrl.text(), 4)
        
        if not valid:
            self.Check_RegValue()
            return
            
        if self.VendorID_M_EN.isChecked():
            cmdText = f"MAOM {ch} 0209 {hex_val}"
        elif self.VendorID_R_EN.isChecked():
            addrs = ["0212", "0292", "0312", "0392"]
            cmdText = f"MAOM 0 {addrs[ch]} {hex_val}"

        self.DRV_Wrt(cmdText, show_flag)
        self.textBrowser_DRVControl_PrintRealTime(f"VG{ch} set: {hex_val} done.")
        if show_flag[1]:
            self.textBrowser_DRVControl_PrintRealTime('')

    def DRV_VGRead_cb(self, show_flag=[1, True, True]):
        if not self._check_vendor_ready(): return
        
        for ch in range(4):
            if self.VendorID_M_EN.isChecked():
                buf = self.DRV_Read(f"MAOM {ch} 0209", show_flag)
            elif self.VendorID_R_EN.isChecked():
                addrs = ["0212", "0292", "0312", "0392"]
                buf = self.DRV_Read(f"MAOM 0 {addrs[ch]}", show_flag)
            
            getattr(self, f"DRV_VG{ch}").setText(buf)
            self._hardware_throttle()
            
        self.textBrowser_DRVControl_PrintRealTime("VG Read done.\n")

    def DRV_PKDRead_cb(self, show_flag=[1, True, True]):
        if not self._check_vendor_ready(): return
        
        A = float(self.Calculate_PKD_A.text())
        B = float(self.Calculate_PKD_B.text())
        do_calc = self.ConvertVolt_PKD_En.isChecked()

        for ch in range(4):
            if self.VendorID_M_EN.isChecked():
                buf = self.DRV_Read(f"MAOM {ch} 027F", show_flag)
            elif self.VendorID_R_EN.isChecked():
                addrs = ["0002", "0006", "000A", "000E"]
                self.DRV_Wrt(f"MAOM 0 020D {addrs[ch]}", [1, False, False]) # 屏蔽中间步骤日志
                self._hardware_throttle()
                buf = self.DRV_Read("MAOM 0 020E", show_flag)
            
            try:
                if do_calc:
                    calc_val = A * int(buf, 16) + B
                    getattr(self, f"DRV_PKD{ch}").setText(f"{calc_val:.2f}")
                    self.textBrowser_DRVControl_PrintRealTime(f"-> PKD{ch}: {calc_val:.2f}V")
                else:
                    getattr(self, f"DRV_PKD{ch}").setText(buf)
            except ValueError:
                getattr(self, f"DRV_PKD{ch}").setText("Err")
                
            self._hardware_throttle()

        self.textBrowser_DRVControl_PrintRealTime("PKD Read Done.\n")

    def DRV_PeakingWrite_cb(self, ch, show_flag=[1, True, True]):
        if not self._check_vendor_ready(): return

        peaking_ctrl = getattr(self, f"DRV_Peaking_{ch}")
        valid, hex_val = self._format_hex_safe(peaking_ctrl.text(), 4)
        
        if not valid:
            self.Check_RegValue()
            return
            
        if self.VendorID_M_EN.isChecked():
            cmdText = f"MAOM {ch} 0210 {hex_val}"
        elif self.VendorID_R_EN.isChecked():
            addrs = ["021D", "029D", "031D", "039D"]
            cmdText = f"MAOM 0 {addrs[ch]} {hex_val}"

        self.DRV_Wrt(cmdText, show_flag)
        self.textBrowser_DRVControl_PrintRealTime(f"Peaking CH{ch} set: {hex_val} done.")

    def DRV_PeakingRead_cb(self, show_flag=[1, True, True]):
        if not self._check_vendor_ready(): return

        for ch in range(4):
            if self.VendorID_M_EN.isChecked():
                buf = self.DRV_Read(f"MAOM {ch} 0210", show_flag)
            elif self.VendorID_R_EN.isChecked():
                addrs = ["021D", "029D", "031D", "039D"]
                buf = self.DRV_Read(f"MAOM 0 {addrs[ch]}", show_flag)
                
            getattr(self, f"DRV_Peaking_{ch}").setText(buf)
            self._hardware_throttle()

        self.textBrowser_DRVControl_PrintRealTime("Peaking Read Done.\n")

    def DRV_VDCOUT_Read_cb(self, show_flag=[1, True, True]):
        if not self._check_vendor_ready(): return

        A = float(self.Calculate_VDCOUT_A.text())
        B = float(self.Calculate_VDCOUT_B.text())
        do_calc = self.ConvertVolt_VDCOUT_En.isChecked()

        for ch in range(4):
            if self.VendorID_M_EN.isChecked():
                buf_p = self.DRV_Read(f"MAOM {ch} 027C", show_flag)
                self._hardware_throttle()
                buf_n = self.DRV_Read(f"MAOM {ch} 027D", show_flag)
            elif self.VendorID_R_EN.isChecked():
                addrs = ["0000", "0004", "0008", "000C"]
                self.DRV_Wrt(f"MAOM 0 020D {addrs[ch]}", [1, False, False]) # 屏蔽中间步骤日志
                self._hardware_throttle()
                buf_p = self.DRV_Read("MAOM 0 020E", show_flag)
                buf_n = "0000"  

            try:
                if do_calc:
                    calc_p = A * int(buf_p, 16) + B
                    calc_n = A * int(buf_n, 16) + B if buf_n != "0000" else 0.0
                    getattr(self, f"DRV_CH{ch}_VDCOUTP").setText(f"{calc_p:.2f}")
                    getattr(self, f"DRV_CH{ch}_VDCOUTN").setText(f"{calc_n:.2f}" if buf_n != "0000" else "")
                    self.textBrowser_DRVControl_PrintRealTime(f"  -> CH{ch} VDC: {calc_p:.2f}V / {calc_n:.2f}V")
                else:
                    getattr(self, f"DRV_CH{ch}_VDCOUTP").setText(buf_p)
                    getattr(self, f"DRV_CH{ch}_VDCOUTN").setText(buf_n if buf_n != "0000" else "")
            except ValueError:
                pass
                
            self._hardware_throttle()

        self.textBrowser_DRVControl_PrintRealTime("VDCOUT Read Done.\n")

    def DRV_TemperatureRead_cb(self, show_flag=[1, True, True]):
        if not self._check_vendor_ready(): return
        
        if self.VendorID_M_EN.isChecked():
            buf = self.DRV_Read('MAOM 0 027B', show_flag)
            try:
                temp_val = int(buf, 16) * self.Calculate_Temperature_A + self.Calculate_Temperature_B
                temp_str = f"{temp_val:.1f}"
            except ValueError:
                temp_str = "Err"
        elif self.VendorID_R_EN.isChecked():
            self.DRV_Wrt('MAOM 0 020D 0001', [1, False, False])
            self._hardware_throttle()
            buf = self.DRV_Read('MAOM 0 020E', show_flag)
            try:
                temp_val = int(buf, 16) * 0.5106 - 261.92
                temp_str = f"{temp_val:.1f}"
            except ValueError:
                temp_str = "Err"

        self.DRV_Temperature.setText(temp_str)
        self.setting_CDM.setValue("setup/DRV_Temperature", temp_str)
        self.textBrowser_DRVControl_PrintRealTime(f"{temp_str} ℃\nDRV Temperature Read done.\n")

    def DRV_ControlMode_Read_cb(self, show_flag=[1, True, True]):
        if not self._check_vendor_ready(): return

        addr = '0207' if self.VendorID_M_EN.isChecked() else '0208'
        buf = self.DRV_Read(f'MAOM 0 {addr}', show_flag)
        self.ControlMode_text.setText(buf)
        self.textBrowser_DRVControl_PrintRealTime(f'ControlMode: {buf}')

        if self.VendorID_M_EN.isChecked():
            self.GainMode_Rd.setEnabled(False)
            self.GainMode_Wrt.setEnabled(False)
            self.GainMode_AGC.setEnabled(False)
            self.GainMode_MGC.setEnabled(False)
            try:
                val = int(buf, 16)
                self.ControlMode_Analog.setChecked(val == 0)
                self.ControlMode_SPI.setChecked(val == 2)
            except ValueError: pass
        else:
            try:
                val = int(buf, 16)
                self.ControlMode_SPI.setChecked(val == 0)
                self.ControlMode_Analog.setChecked(val == 1)
            except ValueError: pass

    def DRV_GainMode_Read_cb(self, show_flag=[1, True, True]):
        if not self._check_vendor_ready(): return
        if not self.VendorID_R_EN.isChecked(): return

        buf = self.DRV_Read('MAOM 0 0207', show_flag)
        self.textBrowser_DRVControl_PrintRealTime(f'GainMode: {buf}')
        self.GainMode_text.setText(buf)
        try:
            val = int(buf, 16)
            self.GainMode_MGC.setChecked(val == 0)
            self.GainMode_AGC.setChecked(val == 1)
        except ValueError: pass

    def DRV_GainMode_Write_cb(self, show_flag=[1, True, True]):
        if not self._check_vendor_ready(): return
        if not self.VendorID_R_EN.isChecked(): return

        valid, hex_val = self._format_hex_safe(self.GainMode_text.text(), 4)
        if valid:
            self.DRV_Wrt(f'MAOM 0 0207 {hex_val}', show_flag)
            self.textBrowser_DRVControl_PrintRealTime(f'GainMode set: {hex_val} done.')
            self._hardware_throttle()
            self.DRV_GainMode_Read_cb(show_flag)
        else:
            self.Check_RegValue()

    def DRV_Convert_Volt_Parameter(self):
        prefix = "setup_DRV/M_" if self.VendorID_M_EN.isChecked() else "setup_DRV/R_"
        self.setting.setValue(f"{prefix}Calculate_PKD_A", self.Calculate_PKD_A.text())    
        self.setting.setValue(f"{prefix}Calculate_PKD_B", self.Calculate_PKD_B.text())  
        self.setting.setValue(f"{prefix}Calculate_VDCOUT_A", self.Calculate_VDCOUT_A.text())  
        self.setting.setValue(f"{prefix}Calculate_VDCOUT_B", self.Calculate_VDCOUT_B.text())    
        self.setting.setValue(f"{prefix}Calculate_Temperature_A", self.Calculate_Temperature_A.text())  
        self.setting.setValue(f"{prefix}Calculate_Temperature_B", self.Calculate_Temperature_B.text())  

    # ------------------- 底层通信接口 (美学净化版) -------------------
    
    def Drv_TxFinish_Check(self, text, TxFlag, show_flag):
        # 【过滤网】：物理拦截 main_cb 借道发送的 DRV Read: 伪装数据，防止重复打印
        if isinstance(text, str) and text.startswith("DRV Read:"):
            return 
            
        if show_flag[1]:
            status = "✔️ 成功" if TxFlag else "❌ 失败"
            self.textBrowser_DRVControl_PrintRealTime(f">> TX: {text} {status}")    

    def _on_read_reply(self, text, success, s_flag):
        if success and isinstance(text, str) and text.startswith("DRV Read:"):
            self._drv_read_result = text.split(":", 1)[1]
            if hasattr(self, '_drv_read_loop') and self._drv_read_loop.isRunning():
                self._drv_read_loop.quit()

    def _on_read_timeout(self):
        self._drv_read_result = "TIMEOUT"
        if hasattr(self, '_drv_read_loop') and self._drv_read_loop.isRunning():
            self._drv_read_loop.quit()
    
    # ------------------- 类级别的槽函数 (Slot) -------------------

    def _on_wrt_reply_capture(self, text, success, s_flag):
        """【写指令回调】：仅用于唤醒写循环"""
        if success and "MAOM" in str(text):
            if hasattr(self, '_drv_wrt_loop') and self._drv_wrt_loop.isRunning():
                self._drv_wrt_loop.quit()

    def _on_read_reply_capture(self, text, success, s_flag):
        """【读指令回调】：仅处理打上 DRV Read: 标签的数据"""
        if success and isinstance(text, str) and text.startswith("DRV Read:"):
            self._drv_read_result = text.split(":", 1)[1]
            if hasattr(self, '_drv_read_loop') and self._drv_read_loop.isRunning():
                self._drv_read_loop.quit()

    # ------------------- 重构后的读写原子接口 -------------------

    def DRV_Wrt(self, DA_cmd='', show_flag=[1, True, True], timeout_ms=500):
        """
        【同步写接口】：确保写指令被底层确认后再返回，清理总线时序
        """
        self._drv_wrt_loop = QtCore.QEventLoop()
        self._drv_wrt_timer = QtCore.QTimer()
        self._drv_wrt_timer.setSingleShot(True)

        # 挂载专用写回调
        self.Drv_TxFinish_flag.connect(self._on_wrt_reply_capture)
        self._drv_wrt_timer.timeout.connect(self._drv_wrt_loop.quit)

        self.Drv_TxSignal.emit(DA_cmd, show_flag, self.ActionNum_0)
        
        self._drv_read_timer.start(timeout_ms)
        self._drv_wrt_loop.exec_() 

        self.Drv_TxFinish_flag.disconnect(self._on_wrt_reply_capture)
        self._drv_wrt_timer.stop()

    def DRV_Read(self, DA_cmd='', show_flag=[1, True, True], timeout_ms=800):
        """
        【同步读接口】：配合拦截器分流，精准获取寄存器值
        """
        self._drv_read_result = ""
        self._drv_read_loop = QtCore.QEventLoop()
        self._drv_read_timer = QtCore.QTimer()
        self._drv_read_timer.setSingleShot(True)

        # 挂载专用读回调
        self.Drv_TxFinish_flag.connect(self._on_read_reply_capture)
        self._drv_read_timer.timeout.connect(self._on_read_timeout)

        self.Drv_TxSignal.emit(DA_cmd, show_flag, self.ActionNum_0)
        
        self._drv_read_timer.start(timeout_ms)
        self._drv_read_loop.exec_() 

        self.Drv_TxFinish_flag.disconnect(self._on_read_reply_capture)
        self._drv_read_timer.stop()

        buf = self._drv_read_result
        if buf == "TIMEOUT" or buf == "":
            return ""

        buf = buf[-4:] if len(buf) >= 4 else buf
        if show_flag[2]:
            self.textBrowser_DRVControl_PrintRealTime(f"<< RX: {buf}")
            
        return buf






if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = DRV_Control_Pane(None, ["0000"]) 
    window.show()
    sys.exit(app.exec_())