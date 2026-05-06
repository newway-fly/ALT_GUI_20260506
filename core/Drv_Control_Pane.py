
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import pyqtSignal,Qt
import sys, os, datetime
sys.path.append(os.getcwd())

from utils.Ui_DRV_Control import Ui_Form
from time import sleep

# import threading
class DRV_Control_Pane(QtWidgets.QWidget,Ui_Form):

    Drv_TxFinish_flag = pyqtSignal(str, bool, list)# DRV Tx完成，传递回来标志位
    Drv_RxData_Reback = pyqtSignal(int,int, list)
    Drv_window_Close = pyqtSignal()
    
 
    def __init__(self, Drv_TxSignal_flag, DRV_Rx_Array):#该类一旦实例化，第一时间执行的内容
        
        super().__init__()#self
        self.setupUi(self)
        
        self.setWindowFlag(Qt.WindowCloseButtonHint)
        self.setWindowFlag(Qt.WindowMinimizeButtonHint,True)
        self.move(200,200)
        self.resize(1200,660)
        
        self.Drv_TxSignal = Drv_TxSignal_flag#传输TX指令
        # self.Drv_RxFinish = Uart_RebackSignal_Flag
        
        self.ActionNum_0 = 0

        self.print_info_all = [1, True, True]
        self.print_info_Wrt = [1, True, False]
        self.print_info_Rd = [1, False, True]
        self.print_info_no = [1, False, False]

        self.DRV_Vendor_Flag = ''
        
        self.Rx_Array = DRV_Rx_Array
        self.Drv_TxFinish = ''
        self.watting_flag = True
        
        # 设置串口配置文件的路径 加载内容
        self.setting = QtCore.QSettings("./data/config_Board.ini", QtCore.QSettings.IniFormat)
        self.setting.setIniCodec("UTF-8")#设置格式

        # 设置CDM配置文件的路径 加载内容
        self.setting_CDM = QtCore.QSettings("./data/config_CDM.ini", QtCore.QSettings.IniFormat)
        self.setting_CDM.setIniCodec("UTF-8")#设置格式
        
        
        self.Drv_TxFinish_flag.connect(self.Drv_TxFinish_Check)
 
        self.DRV_INFO_Read.clicked.connect(lambda: self.DRV_INFO_Read_cb(self.print_info_Rd))
        self.DRV_Reg_Wrt.clicked.connect(lambda: self.DRV_Reg_Wrt_cb(self.print_info_no))
        self.DRV_Reg_Rd.clicked.connect(lambda: self.DRV_Reg_Rd_cb(self.print_info_Wrt))


        #VG读
        self.DRV_VG_Rd.clicked.connect(lambda: self.DRV_VGRead_cb(self.print_info_Rd))
        #VG写
        self.DRV_VG0_Wrt.clicked.connect(lambda: self.DRV_VGWrite_cb(0, self.print_info_no))
        self.DRV_VG1_Wrt.clicked.connect(lambda: self.DRV_VGWrite_cb(1, self.print_info_no))
        self.DRV_VG2_Wrt.clicked.connect(lambda: self.DRV_VGWrite_cb(2, self.print_info_no))
        self.DRV_VG3_Wrt.clicked.connect(lambda: self.DRV_VGWrite_cb(3, self.print_info_no))

        #PKD读
        self.DRV_PKD_Rd.clicked.connect(lambda: self.DRV_PKDRead_cb(self.print_info_Rd))


        #PEAKING读
        self.DRV_Peaking_Rd.clicked.connect(lambda: self.DRV_PeakingRead_cb(self.print_info_Rd))
        #PEAKING写
        self.DRV_Peaking_Wrt_0.clicked.connect(lambda: self.DRV_PeakingWrite_cb(0, self.print_info_no))
        self.DRV_Peaking_Wrt_1.clicked.connect(lambda: self.DRV_PeakingWrite_cb(1, self.print_info_no))
        self.DRV_Peaking_Wrt_2.clicked.connect(lambda: self.DRV_PeakingWrite_cb(2, self.print_info_no))
        self.DRV_Peaking_Wrt_3.clicked.connect(lambda: self.DRV_PeakingWrite_cb(3, self.print_info_no))        

        # #VDCOUT读
        self.DRV_VDCOUT_Rd.clicked.connect(lambda: self.DRV_VDCOUT_Read_cb(self.print_info_Rd))

        # #ControlMode读
        self.ControlMode_Rd.clicked.connect(lambda: self.DRV_ControlMode_Read_cb(self.print_info_Rd))
        
        # #GainMode读
        self.GainMode_Rd.clicked.connect(lambda: self.DRV_GainMode_Read_cb(self.print_info_Rd))
        # #GainMode写
        self.GainMode_Wrt.clicked.connect(lambda: self.DRV_GainMode_Write_cb(self.print_info_Rd))
        
        #Temperature读
        self.DRV_Temperature_Rd.clicked.connect(lambda: self.DRV_TemperatureRead_cb(self.print_info_Rd))

        self.Save_Conv_Volt_Param.clicked.connect(self.DRV_Convert_Volt_Parameter)
        
    def closeEvent(self, a0):
        self.Drv_window_Close.emit()
        return super().closeEvent(a0)

    def Time_record(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    def textBrowser_DRVControl_PrintRealTime(self, text1, flag = True):  # textBrowser实时打印信息
        if flag == True:
            self.textBrowser_DRVControl.append(text1)
            self.cursor = self.textBrowser_DRVControl.textCursor()
            self.textBrowser_DRVControl.moveCursor(self.cursor.End)  # 光标移动到最后，实时信息就可以显示出来
            QtWidgets.QApplication.processEvents()  # 加上此命令，打印过程 GUI不卡顿


    def DRV_INFO_Read_cb(self, show_flag = [1, True, False]):

            self.textBrowser_DRVControl_PrintRealTime('\nReading DRV INFO'+self.Time_record())   

            VendorID = self.DRV_Read('MAOM 0 0200', show_flag)
            self.VendorID_text.setText(VendorID)

            PartID = self.DRV_Read('MAOM 0 0202', show_flag)
            self.PartID_text.setText(str(PartID))

            Version = self.DRV_Read('MAOM 0 0204', show_flag)
            self.Version_text.setText(str(Version))

            # print(self.VendorID_text.text())
            if self.VendorID_text.text() == '4D41':# 界面控件自动 置位厂家选项
                self.DRV_Vendor_Flag = 'M'
                self.VendorID_M_EN.setCheckable(True)
                self.VendorID_M_EN.setChecked(True)
                self.VendorID_R_EN.setChecked(False)
                self.VendorID_M_EN.setStyleSheet('background-color:rgb(0, 255, 0)')
                self.VendorID_R_EN.setStyleSheet('background-color:rgb(255, 255, 255)')
                self.DRV_M_init()
                
                PKD_A = self.setting.value("setup_DRV/M_Calculate_PKD_A")
                PKD_B = self.setting.value("setup_DRV/M_Calculate_PKD_B")     
                self.Calculate_PKD_A.setText(PKD_A)  
                self.Calculate_PKD_B.setText(PKD_B)      
                
                VDCOUT_A = self.setting.value("setup_DRV/M_Calculate_VDCOUT_A")
                VDCOUT_B = self.setting.value("setup_DRV/M_Calculate_VDCOUT_B")     
                self.Calculate_VDCOUT_A.setText(VDCOUT_A)  
                self.Calculate_VDCOUT_B.setText(VDCOUT_B)      
                    
            elif self.VendorID_text.text() == 'E0CF':
                self.DRV_Vendor_Flag = 'R'
                self.VendorID_R_EN.setCheckable(True)
                self.VendorID_R_EN.setChecked(True)
                self.VendorID_M_EN.setChecked(False)
                self.VendorID_M_EN.setStyleSheet('background-color:rgb(255, 255, 255)')
                self.VendorID_R_EN.setStyleSheet('background-color:rgb(0, 255, 0)')
                
                
                PKD_A = self.setting.value("setup_DRV/R_Calculate_PKD_A")
                PKD_B = self.setting.value("setup_DRV/R_Calculate_PKD_B")     
                self.Calculate_PKD_A.setText(PKD_A)  
                self.Calculate_PKD_B.setText(PKD_B)      

                VDCOUT_A = self.setting.value("setup_DRV/R_Calculate_VDCOUT_A")
                VDCOUT_B = self.setting.value("setup_DRV/R_Calculate_VDCOUT_B")     
                self.Calculate_VDCOUT_A.setText(VDCOUT_A)  
                self.Calculate_VDCOUT_B.setText(VDCOUT_B)   
                
            self.textBrowser_DRVControl_PrintRealTime('DRV INFO Read Done'+self.Time_record()+'\n')    

    def DRV_TemperatureRead_cb(self, show_flag = [1, True, True]):
        Buf = ''
        if self.VendorID_M_EN.isChecked() == True:
            DRV_Vendor_Flag = 'M'
            Buf = self.DRV_Read('MAOM 0 027B', show_flag)
            temp_buf = str(int(Buf,16)*0.1933-343.33)[0:4]
            self.DRV_Temperature.setText(temp_buf)
            self.setting_CDM.setValue("setup/DRV_Temperature", temp_buf)
            self.textBrowser_DRVControl_PrintRealTime( str(temp_buf)+ ' ℃')
            self.textBrowser_DRVControl_PrintRealTime('DRV温度读取完成\n')
            
        elif self.VendorID_R_EN.isChecked() == True:
            self.DRV_Wrt('MAOM 0 020D 0001', show_flag)
            Buf = self.DRV_Read('MAOM 0 020E', show_flag)
            temp_buf = str(int(Buf,16)*0.5106-261.92)[0:4]
            self.DRV_Temperature.setText(temp_buf)
            self.setting_CDM.setValue("setup/DRV_Temperature", temp_buf)
            self.textBrowser_DRVControl_PrintRealTime( str(temp_buf)+ ' ℃')
            self.textBrowser_DRVControl_PrintRealTime('DRV温度读取完成\n')

        else:
            self.text = '请先读取一次DRV_INFO,完成DRV型号确认'
            QtWidgets.QMessageBox.information(self, "提示", self.text, QMessageBox.Ok | QMessageBox.Close)

    def DRV_TemperatureRead_Record_cb(self, show_flag = [1, True, False]):
        Buf = ''
        temp_buf = ''
        if self.VendorID_M_EN.isChecked() == True:
            DRV_Vendor_Flag = 'M'
            Buf = self.DRV_Read('MAOM 0 027B', show_flag)
            temp_buf = str(int(Buf,16)*0.1933-343.33)[0:4]
            self.DRV_Temperature.setText(temp_buf)
            
        elif self.VendorID_R_EN.isChecked() == True:
            self.DRV_Wrt('MAOM 0 020D 0001', show_flag)
            Buf = self.DRV_Read('MAOM 0 020E', show_flag)
            temp_buf = str(int(Buf,16)*0.5106-261.92)[0:4]
            self.DRV_Temperature.setText(temp_buf)
        
        self.textBrowser_DRVControl_PrintRealTime('DRV Temperature: '+str(temp_buf)+ ' ℃')
        return temp_buf

    def DRV_Reg_Wrt_cb(self, show_flag = [1, True, False]):
        
        Ch = self.DRV_Ch.text()
        Reg = self.DRV_Reg.text()
        Reg_Value = self.DRV_Reg_Value.text()
        if Reg != '' and Reg_Value != '':
            self.cmdText = 'MAOM ' + str(Ch) + ' ' + str(Reg)  +' '+ str(Reg_Value)+''
            self.DRV_Wrt(self.cmdText, show_flag)
            self.textBrowser_DRVControl_PrintRealTime( 'Reg '+str(Reg)+ ' Write ' + str(Reg_Value)+' Done\n')
        else:
            self.Check_RegValue()             
            self.text = '请先读取一次DRV_INFO,完成DRV型号确认'
            QtWidgets.QMessageBox.information(self, "提示", self.text, QMessageBox.Ok | QMessageBox.Close)
        
    def DRV_Reg_Rd_cb(self, show_flag = [1, True, False]):
        buf = ''
        if self.VendorID_M_EN.isChecked() == True:
            
            Ch = self.DRV_Ch.text()
            Reg = self.DRV_Reg.text()

            if Reg != '':
                buf = self.DRV_Read('MAOM ' + str(Ch) + ' ' + str(Reg) +'', show_flag)
                self.DRV_Reg_Value.setText(buf)
                self.textBrowser_DRVControl_PrintRealTime('Reg '+str(Reg)+ ' Read: '+str(buf) +' Done\n')
            else:
                self.Check_RegValue() 

        elif self.VendorID_R_EN.isChecked() == True:
            Ch = self.DRV_Ch.text()
            Reg = self.DRV_Reg.text()
            if Reg != '':
                buf = self.DRV_Read('MAOM ' + str(Ch) + ' ' + str(Reg) +'', show_flag)
                self.DRV_Reg_Value.setText(buf)
                self.textBrowser_DRVControl_PrintRealTime('Reg '+str(Reg)+ ' Read: '+ str(buf) +' Done\n')
            else:
                self.Check_RegValue() 

        else:
            self.text = '请先读取一次DRV_INFO,完成DRV型号确认'
            QtWidgets.QMessageBox.information(self, "提示", self.text, QMessageBox.Ok | QMessageBox.Close)


    def DRV_M_init(self):

        self.textBrowser_DRVControl_PrintRealTime('\nDRV_M_4D41_Init doing...')
        # self.DRV_Wrt('MAOM 0 0205 0001')
        # self.DRV_Read('MAOM 0 0200',self.print_info_no)
        # self.DRV_Read('MAOM 0 0202',self.print_info_no)
        # self.DRV_Read('MAOM 0 0204',self.print_info_no)
        self.DRV_Wrt('MAOM 0 0207 0002',self.print_info_no)#spi
        self.DRV_Wrt('MAOM 0 027A 018F',self.print_info_no)
        self.DRV_Wrt('MAOM 0 0270 0023',self.print_info_no)
        self.DRV_Wrt('MAOM 0 0272 0009',self.print_info_no)
        self.DRV_Wrt('MAOM 0 0273 00A7',self.print_info_no)
        sleep(0.5)
        self.textBrowser_DRVControl_PrintRealTime('DRV_M_4D41_Init Done\n')

    def DRV_Convert_Volt_Parameter(self):
        if self.VendorID_M_EN.isChecked() == True:
            BUF = self.Calculate_PKD_A.text()
            self.setting.setValue("setup_DRV/M_Calculate_PKD_A",BUF)    
            BUF = self.Calculate_PKD_B.text()
            self.setting.setValue("setup_DRV/M_Calculate_PKD_B",BUF)  
            BUF = self.Calculate_VDCOUT_A.text()
            self.setting.setValue("setup_DRV/M_Calculate_VDCOUT_A",BUF)  
            BUF = self.Calculate_VDCOUT_B.text()
            self.setting.setValue("setup_DRV/M_Calculate_VDCOUT_B",BUF)    
        elif self.VendorID_R_EN.isChecked() == True:
            BUF = self.Calculate_PKD_A.text()
            self.setting.setValue("setup_DRV/R_Calculate_PKD_A",BUF)    
            BUF = self.Calculate_PKD_B.text()
            self.setting.setValue("setup_DRV/R_Calculate_PKD_B",BUF)  
            BUF = self.Calculate_VDCOUT_A.text()
            self.setting.setValue("setup_DRV/R_Calculate_VDCOUT_A",BUF)  
            BUF = self.Calculate_VDCOUT_B.text()
            self.setting.setValue("setup_DRV/R_Calculate_VDCOUT_B",BUF)             
    
    def Check_RegValue(self):
        self.text = 'The Value cannot be empty!'
        
        QtWidgets.QMessageBox.information(self, "提示", self.text, QMessageBox.Ok | QMessageBox.Close)

    def DRV_VGWrite_cb(self, ch, show_flag = [1, True, False]):
        VG_Ch= ''
        cmdText = ''
        if self.VendorID_M_EN.isChecked() == True:
            
            if ch == 0:
                VGValue = self.DRV_VG0.text()
                if VGValue != '':
                    cmdText = 'MAOM 0 0209 '+str(VGValue)
                    VG_Ch = 'VG0'
                else:
                    self.Check_RegValue()

            elif ch == 1:
                VGValue = self.DRV_VG1.text()
                if VGValue != '':
                    cmdText = 'MAOM 1 0209 '+str(VGValue)
                    VG_Ch = 'VG1'
                else:
                    self.Check_RegValue()

            elif ch == 2:
                VGValue = self.DRV_VG2.text()
                if VGValue != '':
                    cmdText = 'MAOM 2 0209 '+str(VGValue)
                    VG_Ch = 'VG2'
                else:
                    self.Check_RegValue()

            elif ch == 3:
                VGValue = self.DRV_VG3.text()
                if VGValue != '':
                    cmdText = 'MAOM 3 0209 '+str(VGValue)
                    VG_Ch = 'VG3'
                else:
                    self.Check_RegValue()   

            self.DRV_Wrt(cmdText, show_flag)
            self.textBrowser_DRVControl_PrintRealTime(VG_Ch+'设置: '+str(VGValue)+' 成功')
            if show_flag == True:
                self.textBrowser_DRVControl_PrintRealTime('') 
            
        elif self.VendorID_R_EN.isChecked() == True:
  
            if ch == 0:
                VGValue = self.DRV_VG0.text()
                if VGValue != '':
                    cmdText = 'MAOM 0 0212 '+str(VGValue)
                    VG_Ch = 'VG0'
                else:
                    self.Check_RegValue() 

            elif ch == 1:
                VGValue = self.DRV_VG1.text()
                if VGValue != '':
                    cmdText = 'MAOM 0 0292 '+str(VGValue)
                    VG_Ch = 'VG1'
                else:
                    self.Check_RegValue() 

            elif ch == 2:
                VGValue = self.DRV_VG2.text()
                if VGValue != '':
                    cmdText = 'MAOM 0 312 '+str(VGValue)
                    VG_Ch = 'VG2'
                else:
                    self.Check_RegValue() 

            elif ch == 3:
                VGValue = self.DRV_VG3.text()
                if VGValue != '':
                    cmdText = 'MAOM 0 392 '+str(VGValue)
                    VG_Ch = 'VG3' 
                else:
                    self.Check_RegValue()       

            self.DRV_Wrt(cmdText, show_flag)
            self.textBrowser_DRVControl_PrintRealTime(VG_Ch+'设置: '+str(VGValue)+' 成功') 
            if show_flag == True:
                self.textBrowser_DRVControl_PrintRealTime('') 
        else:
            self.text = '请先读取一次DRV_INFO,完成DRV型号确认'
            QtWidgets.QMessageBox.information(self, "提示", self.text, QMessageBox.Ok | QMessageBox.Close)

    def DRV_VGRead_cb(self, show_flag = [1, True, True]):

        if self.VendorID_M_EN.isChecked() == True:

            VG0 = self.DRV_Read('MAOM 0 0209', show_flag)
            self.DRV_VG0.setText(VG0)

            VG1 = self.DRV_Read('MAOM 1 0209', show_flag)
            self.DRV_VG1.setText(VG1)

            VG2 = self.DRV_Read('MAOM 2 0209', show_flag)
            self.DRV_VG2.setText(VG2)

            VG3 = self.DRV_Read('MAOM 3 0209', show_flag)
            self.DRV_VG3.setText(VG3)       
            self.textBrowser_DRVControl_PrintRealTime('VG读取完成')
            self.textBrowser_DRVControl_PrintRealTime('') 
            
        elif self.VendorID_R_EN.isChecked() == True:
  
            VG0 = self.DRV_Read('MAOM 0 0212', show_flag)
            self.DRV_VG0.setText(VG0)

            VG1 = self.DRV_Read('MAOM 0 0292', show_flag)
            self.DRV_VG1.setText(VG1)

            VG2 = self.DRV_Read('MAOM 0 0312', show_flag)
            self.DRV_VG2.setText(VG2)

            VG3 = self.DRV_Read('MAOM 0 0392', show_flag)
            self.DRV_VG3.setText(VG3)   

            self.textBrowser_DRVControl_PrintRealTime('VG读取完成')
            self.textBrowser_DRVControl_PrintRealTime('') 

        else:
            self.text = '请先读取一次DRV_INFO,完成DRV型号确认'
            QtWidgets.QMessageBox.information(self, "提示", self.text, QMessageBox.Ok | QMessageBox.Close)

    def DRV_PKDRead_cb(self, show_flag = [1, True, True]):
        Buf = ''
        if self.VendorID_M_EN.isChecked() == True:
            
            if self.ConvertVolt_En.isChecked() != True:
                Buf = self.DRV_Read('MAOM 0 027F', show_flag)
                self.DRV_PKD0.setText(Buf)
                Buf = self.DRV_Read('MAOM 1 027F', show_flag)
                self.DRV_PKD1.setText(Buf)
                Buf = self.DRV_Read('MAOM 2 027F', show_flag)
                self.DRV_PKD2.setText(Buf)
                Buf = self.DRV_Read('MAOM 3 027F', show_flag)
                self.DRV_PKD3.setText(Buf)      
            else:
                Buf = self.DRV_Read('MAOM 0 027F', show_flag)
                Buf1 = float(self.Calculate_PKD_A.text())*int(Buf,16)+float(self.Calculate_PKD_B.text())
                self.DRV_PKD0.setText(str(Buf1)[:4])
                Buf = self.DRV_Read('MAOM 1 027F', show_flag)
                Buf2 = float(self.Calculate_PKD_A.text())*int(Buf,16)+float(self.Calculate_PKD_B.text())
                self.DRV_PKD1.setText(str(Buf2)[:4])
                Buf = self.DRV_Read('MAOM 2 027F', show_flag)
                Buf3 = float(self.Calculate_PKD_A.text())*int(Buf,16)+float(self.Calculate_PKD_B.text())
                self.DRV_PKD2.setText(str(Buf3)[:4])
                Buf = self.DRV_Read('MAOM 3 027F', show_flag)
                Buf4 = float(self.Calculate_PKD_A.text())*int(Buf,16)+float(self.Calculate_PKD_B.text())
                self.DRV_PKD3.setText(str(Buf4)[:4])                     
                self.textBrowser_DRVControl_PrintRealTime(str(Buf1)[:4]+'V')
                self.textBrowser_DRVControl_PrintRealTime(str(Buf2)[:4]+'V')
                self.textBrowser_DRVControl_PrintRealTime(str(Buf3)[:4]+'V')
                self.textBrowser_DRVControl_PrintRealTime(str(Buf4)[:4]+'V')
            self.textBrowser_DRVControl_PrintRealTime('PKD Read Done.\n')
            
        elif self.VendorID_R_EN.isChecked() == True:
            if self.ConvertVolt_En.isChecked() != True:
                DRV_Vendor_Flag = 'R'
                self.DRV_Wrt('MAOM 0 020D 0002', show_flag)
                Buf = self.DRV_Read('MAOM 0 020E', show_flag)
                self.DRV_PKD0.setText(Buf)

                self.DRV_Wrt('MAOM 0 020D 0006', show_flag)
                Buf = self.DRV_Read('MAOM 0 020E', show_flag)
                self.DRV_PKD1.setText(Buf)

                self.DRV_Wrt('MAOM 0 020D 000A', show_flag)
                Buf = self.DRV_Read('MAOM 0 020E', show_flag)
                self.DRV_PKD2.setText(Buf)

                self.DRV_Wrt('MAOM 0 020D 000E', show_flag)
                Buf = self.DRV_Read('MAOM 0 020E', show_flag)
                self.DRV_PKD3.setText(Buf)   
            else:
                self.DRV_Wrt('MAOM 0 020D 0002', show_flag)
                Buf = self.DRV_Read('MAOM 0 020E', show_flag)
                Buf1 = float(self.Calculate_PKD_A.text())*int(Buf,16)+float(self.Calculate_PKD_B.text())
                self.DRV_PKD0.setText(str(Buf1)[:4])
                self.DRV_Wrt('MAOM 0 020D 0006', show_flag)
                Buf = self.DRV_Read('MAOM 0 020E', show_flag)
                Buf2 = float(self.Calculate_PKD_A.text())*int(Buf,16)+float(self.Calculate_PKD_B.text())
                self.DRV_PKD1.setText(str(Buf2)[:4])
                self.DRV_Wrt('MAOM 0 020D 000A', show_flag)
                Buf = self.DRV_Read('MAOM 0 020E', show_flag)
                Buf3 = float(self.Calculate_PKD_A.text())*int(Buf,16)+float(self.Calculate_PKD_B.text())
                self.DRV_PKD2.setText(str(Buf3)[:4])
                self.DRV_Wrt('MAOM 0 020D 000E', show_flag)
                Buf = self.DRV_Read('MAOM 0 020E', show_flag)
                Buf4 = float(self.Calculate_PKD_A.text())*int(Buf,16)+float(self.Calculate_PKD_B.text())
                self.DRV_PKD3.setText(str(Buf4)[:4])     
                self.textBrowser_DRVControl_PrintRealTime(str(Buf1)[:4]+'V')
                self.textBrowser_DRVControl_PrintRealTime(str(Buf2)[:4]+'V')
                self.textBrowser_DRVControl_PrintRealTime(str(Buf3)[:4]+'V')
                self.textBrowser_DRVControl_PrintRealTime(str(Buf4)[:4]+'V')
                    
            self.textBrowser_DRVControl_PrintRealTime('PKD Read Done.\n')
        else:
            self.text = '请先读取一次DRV_INFO,完成DRV型号确认'
            QtWidgets.QMessageBox.information(self, "提示", self.text, QMessageBox.Ok | QMessageBox.Close)

    def DRV_PeakingWrite_cb(self, ch, show_flag = [1, True, True]):

        if self.VendorID_M_EN.isChecked() == True:
            
            if ch == 0:
                PeakingValue = self.DRV_Peaking_0.text()
                if PeakingValue != '':
                    self.cmdText = 'MAOM 0 0210 '+str(PeakingValue)+''
    
                    self.DRV_Wrt(self.cmdText, show_flag)
                    self.textBrowser_DRVControl_PrintRealTime('Peaking CH0设置: '+str(PeakingValue)+' 成功')
                else:
                    self.Check_RegValue()

            elif ch == 1:
                PeakingValue = self.DRV_Peaking_1.text()
                if PeakingValue != '':
                    self.cmdText = 'MAOM 1 0210 '+str(PeakingValue)+''
         
                    self.DRV_Wrt(self.cmdText, show_flag)
                    self.textBrowser_DRVControl_PrintRealTime('Peaking CH1设置: '+str(PeakingValue)+' 成功')
                else:
                    self.Check_RegValue()

            elif ch == 2:
                PeakingValue = self.DRV_Peaking_2.text()
                if PeakingValue != '':
                    self.cmdText = 'MAOM 2 0210 '+str(PeakingValue)+''
             
                    self.DRV_Wrt(self.cmdText, show_flag)
                    self.textBrowser_DRVControl_PrintRealTime('Peaking CH2设置: '+str(PeakingValue)+' 成功')
                else:
                    self.Check_RegValue()

            elif ch == 3:
                PeakingValue = self.DRV_Peaking_3.text()
                if PeakingValue != '':
                    self.cmdText = 'MAOM 3 0210 '+str(PeakingValue)+''
          
                    self.DRV_Wrt(self.cmdText, show_flag)
                    self.textBrowser_DRVControl_PrintRealTime('Peaking CH3设置: '+str(PeakingValue)+' 成功')     
                else:
                    self.Check_RegValue()   
            else:
                pass
            
        elif self.VendorID_R_EN.isChecked() == True:
  
            if ch == 0:
                PeakingValue = self.DRV_Peaking_0.text()
                if PeakingValue != '':
                    self.cmdText = 'MAOM 0 021D '+str(PeakingValue)+''
        
                    self.DRV_Wrt(self.cmdText, show_flag)
                    self.textBrowser_DRVControl_PrintRealTime('VG0设置: '+str(PeakingValue)+' 成功')
                else:
                    self.Check_RegValue() 

            elif ch == 1:
                PeakingValue = self.DRV_Peaking_1.text()
                if PeakingValue != '':
                    self.cmdText = 'MAOM 0 029D '+str(PeakingValue)+''

                    self.DRV_Wrt(self.cmdText, show_flag)
                    self.textBrowser_DRVControl_PrintRealTime('VG1设置: '+str(PeakingValue)+' 成功')
                else:
                    self.Check_RegValue() 

            elif ch == 2:
                PeakingValue = self.DRV_Peaking_2.text()
                if PeakingValue != '':
                    self.cmdText = 'MAOM 0 31D '+str(PeakingValue)+''
          
                    self.DRV_Wrt(self.cmdText, show_flag)
                    self.textBrowser_DRVControl_PrintRealTime('VG2设置: '+str(PeakingValue)+' 成功')
                else:
                    self.Check_RegValue() 

            elif ch == 3:
                PeakingValue = self.DRV_Peaking_3.text()
                if PeakingValue != '':
                    self.cmdText = 'MAOM 0 39D '+str(PeakingValue)+''
       
                    self.DRV_Wrt(self.cmdText, show_flag)
                    self.textBrowser_DRVControl_PrintRealTime('VG3设置: '+str(PeakingValue)+' 成功')  
                else:
                    self.Check_RegValue()       
            else:
                pass  

        else:
            self.text = '请先读取一次DRV_INFO,完成DRV型号确认'
            
            QtWidgets.QMessageBox.information(self, "提示", self.text, QMessageBox.Ok | QMessageBox.Close)

    def DRV_PeakingRead_cb(self, show_flag = [1, True, True]):
        Buf = ''
        if self.VendorID_M_EN.isChecked() == True:
            
            DRV_Vendor_Flag = 'M'
            Buf =self.DRV_Read('MAOM 0 0210', show_flag)
            self.DRV_Peaking_0.setText(Buf)

            Buf =self.DRV_Read('MAOM 1 0210', show_flag)
            self.DRV_Peaking_1.setText(Buf)

            Buf =self.DRV_Read('MAOM 2 0210', show_flag)
            self.DRV_Peaking_2.setText(Buf)

            Buf =self.DRV_Read('MAOM 3 0210', show_flag)
            self.DRV_Peaking_3.setText(Buf)       

            self.textBrowser_DRVControl_PrintRealTime('Peaking Read Done.\n')
            
        elif self.VendorID_R_EN.isChecked() == True:

            Buf =self.DRV_Read('MAOM 0 021D', show_flag)
            self.DRV_Peaking_0.setText(Buf)

            Buf =self.DRV_Read('MAOM 0 029D', show_flag)
            self.DRV_Peaking_1.setText(Buf)

            Buf =self.DRV_Read('MAOM 0 031D', show_flag)
            self.DRV_Peaking_2.setText(Buf)

            Buf =self.DRV_Read('MAOM 0 039D', show_flag)
            self.DRV_Peaking_3.setText(Buf)   
            
            self.textBrowser_DRVControl_PrintRealTime('Peaking读取完成\n')

        else:
            self.text = '请先读取一次DRV_INFO,完成DRV型号确认'
            
            QtWidgets.QMessageBox.information(self, "提示", self.text, QMessageBox.Ok | QMessageBox.Close)

    def DRV_VDCOUT_Read_cb(self, show_flag = [1, True, True]):
        Buf = ''
        if self.VendorID_M_EN.isChecked() == True:
            if self.ConvertVolt_En.isChecked() != True:
                DRV_Vendor_Flag = 'M'

                Buf = self.DRV_Read('MAOM 0 027C', show_flag)
                self.DRV_CH0_VDCOUTP.setText(Buf)
                
                Buf = self.DRV_Read('MAOM 0 027D', show_flag)
                self.DRV_CH0_VDCOUTN.setText(Buf)
                
                Buf = self.DRV_Read('MAOM 1 027C', show_flag)
                self.DRV_CH1_VDCOUTP.setText(Buf)
                
                Buf = self.DRV_Read('MAOM 1 027D', show_flag)
                self.DRV_CH1_VDCOUTN.setText(Buf)
                
                Buf = self.DRV_Read('MAOM 2 027C', show_flag)
                self.DRV_CH2_VDCOUTP.setText(Buf)
                
                Buf = self.DRV_Read('MAOM 2 027D', show_flag)
                self.DRV_CH2_VDCOUTN.setText(Buf)
                
                Buf = self.DRV_Read('MAOM 3 027C', show_flag)
                self.DRV_CH3_VDCOUTP.setText(Buf)
                
                Buf = self.DRV_Read('MAOM 3 027D', show_flag)
                self.DRV_CH3_VDCOUTN.setText(Buf)

            else:
                Buf = self.DRV_Read('MAOM 0 027C', show_flag)
                Buf1 = float(self.Calculate_VDCOUT_A.text())*int(Buf,16)+float(self.Calculate_VDCOUT_B.text())
                self.DRV_CH0_VDCOUTP.setText(str(Buf1)[:4])
                
                Buf = self.DRV_Read('MAOM 0 027D', show_flag)
                Buf2 = float(self.Calculate_VDCOUT_A.text())*int(Buf,16)+float(self.Calculate_VDCOUT_B.text())
                self.DRV_CH0_VDCOUTN.setText(str(Buf2)[:4])
                
                Buf = self.DRV_Read('MAOM 1 027C', show_flag)
                Buf3 = float(self.Calculate_VDCOUT_A.text())*int(Buf,16)+float(self.Calculate_VDCOUT_B.text())
                self.DRV_CH1_VDCOUTP.setText(str(Buf3)[:4])
                
                Buf = self.DRV_Read('MAOM 1 027D', show_flag)
                Buf4 = float(self.Calculate_VDCOUT_A.text())*int(Buf,16)+float(self.Calculate_VDCOUT_B.text())
                self.DRV_CH1_VDCOUTN.setText(str(Buf4)[:4])
                
                Buf = self.DRV_Read('MAOM 2 027C', show_flag)
                Buf5 = float(self.Calculate_VDCOUT_A.text())*int(Buf,16)+float(self.Calculate_VDCOUT_B.text())
                self.DRV_CH2_VDCOUTP.setText(str(Buf5)[:4])
                
                Buf = self.DRV_Read('MAOM 2 027D', show_flag)
                Buf6 = float(self.Calculate_VDCOUT_A.text())*int(Buf,16)+float(self.Calculate_VDCOUT_B.text())
                self.DRV_CH2_VDCOUTN.setText(str(Buf6)[:4])
                
                Buf = self.DRV_Read('MAOM 3 027C', show_flag)
                Buf7 = float(self.Calculate_VDCOUT_A.text())*int(Buf,16)+float(self.Calculate_VDCOUT_B.text())
                self.DRV_CH3_VDCOUTP.setText(str(Buf7)[:4])
                
                Buf = self.DRV_Read('MAOM 3 027D', show_flag)
                Buf8 = float(self.Calculate_VDCOUT_A.text())*int(Buf,16)+float(self.Calculate_VDCOUT_B.text())
                self.DRV_CH3_VDCOUTN.setText(str(Buf8)[:4])

   
                self.textBrowser_DRVControl_PrintRealTime(str(Buf1)[:4]+'V')
                self.textBrowser_DRVControl_PrintRealTime(str(Buf2)[:4]+'V')
                self.textBrowser_DRVControl_PrintRealTime(str(Buf3)[:4]+'V')
                self.textBrowser_DRVControl_PrintRealTime(str(Buf4)[:4]+'V')
                self.textBrowser_DRVControl_PrintRealTime(str(Buf5)[:4]+'V')
                self.textBrowser_DRVControl_PrintRealTime(str(Buf6)[:4]+'V')
                self.textBrowser_DRVControl_PrintRealTime(str(Buf7)[:4]+'V')
                self.textBrowser_DRVControl_PrintRealTime(str(Buf8)[:4]+'V')




            self.textBrowser_DRVControl_PrintRealTime('VDCOUT读取完成\n')
            
        elif self.VendorID_R_EN.isChecked() == True:
            if self.ConvertVolt_En.isChecked() != True:
                DRV_Vendor_Flag = 'M'
                self.DRV_Wrt('MAOM 0 020D 0000', show_flag)
                Buf = self.DRV_Read('MAOM 0 020E', show_flag)
                
                self.DRV_CH0_VDCOUTP.setText(Buf)
                self.DRV_CH0_VDCOUTN.setText('')

                self.DRV_Wrt('MAOM 0 020D 0004', show_flag)
                Buf = self.DRV_Read('MAOM 0 020E', show_flag)
                
                self.DRV_CH1_VDCOUTP.setText(Buf)
                self.DRV_CH1_VDCOUTN.setText('')

                self.DRV_Wrt('MAOM 0 020D 0008', show_flag)
                Buf = self.DRV_Read('MAOM 0 020E', show_flag)
                
                self.DRV_CH2_VDCOUTP.setText(Buf)
                self.DRV_CH2_VDCOUTN.setText('')

                self.DRV_Wrt('MAOM 0 020D 000C', show_flag)
                Buf = self.DRV_Read('MAOM 0 020E', show_flag)
                
                self.DRV_CH3_VDCOUTP.setText(Buf)  
                self.DRV_CH3_VDCOUTN.setText('') 
            else:
                self.DRV_Wrt('MAOM 0 020D 0000', show_flag)
                Buf = self.DRV_Read('MAOM 0 020E', show_flag)
                Buf1 = float(self.Calculate_VDCOUT_A.text())*int(Buf,16)+float(self.Calculate_VDCOUT_B.text())
                self.DRV_CH0_VDCOUTP.setText(str(Buf1)[:4])
                self.DRV_CH0_VDCOUTN.setText('')

                self.DRV_Wrt('MAOM 0 020D 0004', show_flag)
                Buf = self.DRV_Read('MAOM 0 020E', show_flag)
                Buf2 = float(self.Calculate_VDCOUT_A.text())*int(Buf,16)+float(self.Calculate_VDCOUT_B.text())
                self.DRV_CH1_VDCOUTP.setText(str(Buf2)[:4])
                self.DRV_CH1_VDCOUTN.setText('')

                self.DRV_Wrt('MAOM 0 020D 0008', show_flag)
                Buf = self.DRV_Read('MAOM 0 020E', show_flag)
                Buf3 = float(self.Calculate_VDCOUT_A.text())*int(Buf,16)+float(self.Calculate_VDCOUT_B.text())
                self.DRV_CH2_VDCOUTP.setText(str(Buf3)[:4])
                self.DRV_CH2_VDCOUTN.setText('')

                self.DRV_Wrt('MAOM 0 020D 000C', show_flag)
                Buf = self.DRV_Read('MAOM 0 020E', show_flag)
                Buf4 = float(self.Calculate_VDCOUT_A.text())*int(Buf,16)+float(self.Calculate_VDCOUT_B.text())
                self.DRV_CH3_VDCOUTP.setText(str(Buf4)[:4])  
                self.DRV_CH3_VDCOUTN.setText('')     
                

                self.textBrowser_DRVControl_PrintRealTime(str(Buf1)[:4]+'V')
                self.textBrowser_DRVControl_PrintRealTime(str(Buf2)[:4]+'V')
                self.textBrowser_DRVControl_PrintRealTime(str(Buf3)[:4]+'V')
                self.textBrowser_DRVControl_PrintRealTime(str(Buf4)[:4]+'V')
        
            
            self.textBrowser_DRVControl_PrintRealTime('VDCOUT读取完成\n')
        else:
            self.text = '请先读取一次DRV_INFO,完成DRV型号确认'
            QtWidgets.QMessageBox.information(self, "提示", self.text, QMessageBox.Ok | QMessageBox.Close)
  
    def DRV_ControlMode_Read_cb(self, show_flag = [1, True, True]):
        Buf = ''
        if self.VendorID_M_EN.isChecked() == True:
            DRV_Vendor_Flag = 'M'

            Buf = self.DRV_Read('MAOM 0 0207', show_flag)
            
            self.ControlMode_text.setText(Buf)
            self.textBrowser_DRVControl_PrintRealTime('ControlMode: '+str(Buf))

            self.GainMode_Rd.setEnabled(False)
            self.GainMode_Wrt.setEnabled(False)
            self.GainMode_AGC.setEnabled(False)
            self.GainMode_MGC.setEnabled(False)   

            if int(Buf) == 0:
                self.ControlMode_Analog.setChecked(True)
                self.ControlMode_SPI.setEnabled(False)
            elif int(Buf) == 2:
                self.ControlMode_Analog.setEnabled(False)
                self.ControlMode_SPI.setChecked(True)
      
            
        elif self.VendorID_R_EN.isChecked() == True:
  
            Buf = self.DRV_Read('MAOM 0 0208', show_flag)
            
            self.ControlMode_text.setText(Buf)
            if int(Buf) == 0:
                self.ControlMode_Analog.setEnabled(False)
                self.ControlMode_SPI.setChecked(True)
            elif int(Buf) == 1:
                self.ControlMode_Analog.setChecked(True)
                self.ControlMode_SPI.setEnabled(False)

        else:
            self.text = '请先读取一次DRV_INFO,完成DRV型号确认'
            
            QtWidgets.QMessageBox.information(self, "提示", self.text, QMessageBox.Ok | QMessageBox.Close)

    def DRV_GainMode_Write_cb(self, show_flag = [1, True, True]):

        if self.VendorID_R_EN.isChecked() == True:
            Buf = ''
            GainModeValue = self.GainMode_text.text()
            if GainModeValue != '':
                self.cmdText = 'MAOM 0 0207 '+str(GainModeValue)+''
                self.DRV_Wrt(self.cmdText, show_flag)
                self.textBrowser_DRVControl_PrintRealTime('GainMode设置: '+str(GainModeValue)+' 成功')

                #设置后 读取寄存器值做界面状态的改变
                Buf = self.DRV_Read('MAOM 0 0207', show_flag)
                # 
                self.GainMode_text.setText(Buf)

                if int(Buf) == 0:
                    self.GainMode_AGC.setEnabled(False)
                    self.GainMode_MGC.setEnabled(True)
                    self.GainMode_MGC.setChecked(True)
                    
                elif int(Buf) == 1:
                    self.GainMode_AGC.setEnabled(True)
                    self.GainMode_AGC.setChecked(True)
                    self.GainMode_MGC.setEnabled(False)


            else:
                self.Check_RegValue()
        else:
            self.text = '请先读取一次DRV_INFO,完成DRV型号确认'
            
            QtWidgets.QMessageBox.information(self, "提示", self.text, QMessageBox.Ok | QMessageBox.Close)

    def DRV_GainMode_Read_cb(self, show_flag = [1, True, True]):
        Buf = ''
        if self.VendorID_R_EN.isChecked() == True:
  
            Buf = self.DRV_Read('MAOM 0 0207', show_flag)
            self.textBrowser_DRVControl_PrintRealTime('GainMode: '+str(Buf))
            self.GainMode_text.setText(Buf)

            if int(Buf) == 0:
                self.GainMode_AGC.setEnabled(False)
                self.GainMode_MGC.setChecked(True)
            elif int(Buf) == 1:
                self.GainMode_AGC.setChecked(True)
                self.GainMode_MGC.setEnabled(False)

        else:
            self.text = '请先读取一次DRV_INFO,完成DRV型号确认'
            QtWidgets.QMessageBox.information(self, "提示", self.text, QMessageBox.Ok | QMessageBox.Close)

    def Drv_TxFinish_Check(self, text, TxFlag, show_flag): #‘写’指令 打印
        if show_flag[1] == True:
            if TxFlag == True:
                text = "%s"% text+" 已发送  " 
            else:
                text = "%s"% text+" 发送失败  " 
            self.textBrowser_DRVControl_PrintRealTime(text)    
                
    def DRV_Read(self, DA_cmd='', show_flag=[1,True,True]): #‘读’指令，先下发指令，然后读取串口所有回传的信息
        buf = ''
        self.Drv_TxSignal.emit(DA_cmd, show_flag, self.ActionNum_0)#发送读的指令
        buf = self.Rx_Array[0]
        #处理回复的信息
        if show_flag[2] == False:
            self.textBrowser_DRVControl_PrintRealTime(buf,show_flag[2])
        else:
            self.textBrowser_DRVControl_PrintRealTime(buf)
        return buf[-4:]
        
    def DRV_Wrt(self, DA_cmd='', show_flag=[1,True,True]): #‘读’指令，先下发指令，然后读取串口所有回传的信息

        self.Drv_TxSignal.emit(DA_cmd, show_flag, self.ActionNum_0)#发送读的指令
      


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    
    window = DRV_Control_Pane()
    window.show()

    sys.exit(app.exec_())
