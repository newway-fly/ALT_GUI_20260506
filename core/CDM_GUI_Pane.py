from PyQt5 import QtWidgets,QtCore
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import pyqtSignal
from time import sleep

import serial.tools.list_ports
import sys,datetime
# import os
# sys.path.append(os.getcwd())

from utils.Ui_CDM_GUI import Ui_Form
from utils.UartA import Uart_Tool


from core.Drv_Control_Pane import DRV_Control_Pane


class CDM_GUI_Pane(QtWidgets.QWidget,Ui_Form):

    Uart_TxFinish_Flag = pyqtSignal(bool, list, str, str)#串口 tx信息、发送成功标志位、是否打印标志位
    Uart_RebackSignal = pyqtSignal(list, str , int, str)#串口回传的信息：个数 & 数据接收完成的标志 & 是否由线程触发->打印信息

    DRV_Tx = pyqtSignal(str, list, int)      #串口 tx信息、发送成功标志位、是否打印标志位
    DRV_RebackSignal = pyqtSignal(list, str ,int)#串口回传的信息：个数 & 数据接收完成的标志 & 是否由线程触发->打印信息
    
    LogPrint = pyqtSignal(str, list)
    
    def __init__(self, parent=None, *args,**kwargs, ):#该类一旦实例化，第一时间执行的内容
        
        super().__init__(parent, *args,**kwargs)#
        #上面直接继承父类QtWidgets.QWidget，会覆盖_rc的背景图，增加这句命令即可
        # self.setAttribute(Qt.WA_StyledBackground, True)
        self.setupUi(self)

        self.DRV_Control_Pane_show = ''

        
        self.print_info_all     = [1, True, True]
        self.print_info_fast    = [1, True, False]
        self.print_info_no      = [1, False, False]

        self.DoneNum_0 = 0
        self.DoneNum_1 = 1
        self.DoneNum_2 = 2
        self.DoneNum_3 = 3
        self.DoneNum_4 = 4
        self.DoneNum_5 = 5
        self.DoneNum_6 = 6
        self.DoneNum_7 = 7
        self.DoneNum_8 = 8
        self.DoneNum_9 = 9

        self.HeaterR_Volt_Name_list = ['',"XI_HeaterR_P_Volt","XI_HeaterR_N_Volt","XQ_HeaterR_P_Volt","XQ_HeaterR_N_Volt",
                                            "YI_HeaterR_P_Volt","YI_HeaterR_N_Volt","YQ_HeaterR_P_Volt","YQ_HeaterR_N_Volt",
                                                "XP_HeaterR_P_Volt","XP_HeaterR_N_Volt","YP_HeaterR_P_Volt","YP_HeaterR_N_Volt",
                                                    "ch7_HeaterR_P_Volt","ch7_HeaterR_N_Volt","ch8_HeaterR_P_Volt","ch8_HeaterR_N_Volt"]   
        self.HeaterR_Curr_Name_list = ['',"XI_HeaterR_P_Curr","XI_HeaterR_N_Curr","XQ_HeaterR_P_Curr","XQ_HeaterR_N_Curr",
                                            "YI_HeaterR_P_Curr","YI_HeaterR_N_Curr","YQ_HeaterR_P_Curr","YQ_HeaterR_N_Curr",
                                                "XP_HeaterR_P_Curr","XP_HeaterR_N_Curr","YP_HeaterR_P_Curr","YP_HeaterR_N_Curr",
                                                    "ch7_HeaterR_P_Curr","ch7_HeaterR_N_Curr","ch8_HeaterR_P_Curr","ch8_HeaterR_N_Curr"]      
           
        self.HeaterR_Name_list = ['','XI_HeaterR_P','XI_HeaterR_N','XQ_HeaterR_P','XQ_HeaterR_N',
                                'YI_HeaterR_P','YI_HeaterR_N','YQ_HeaterR_P','YQ_HeaterR_N',
                                'XP_HeaterR_P','XP_HeaterR_N','YP_HeaterR_P','YP_HeaterR_N']              
        self.Rx_Array_ID = 0
        self.Rx_Array = ['']*40#传递串口的Rx数据


        # 设置串口配置文件的路径 加载内容
        self.setting = QtCore.QSettings("./data/config_Board.ini", QtCore.QSettings.IniFormat)
        self.setting.setIniCodec("UTF-8")#设置格式

        self.SerialPortA_Baud = self.setting.value("setup_SerialPortA/SerialPortA_COM")
        self.SerialPortA.addItem(self.setting.value("setup_SerialPortA/SerialPortA_COM"))

        self.STM32_ADC_VREF = float(self.setting.value("setup_Power/STM32_ADC_VREF"))

        # if self.setting.value("setup/SerialPortA_ConnectFlag") != True:
        self.setting.setValue("setup/SerialPortA_ConnectFlag", False)
        

        # 设置CDM配置文件的路径 加载内容
        self.setting_CDM = QtCore.QSettings("./data/config_CDM.ini", QtCore.QSettings.IniFormat)
        self.setting_CDM.setIniCodec("UTF-8")#设置格式
        
        # Equipment_Control_name = "Equipment_Control_V3.6/data/setting_equipment.ini"
        Equipment_Control_name = str(self.setting.value("directory_path/Equipment_Control_name"))+"/data/setting_equipment.ini"

        #映射到setting_equipment.ini
        parent_directory_path = self.setting.value("directory_path/parent_directory_path")
        self.setting_equipment = QtCore.QSettings(str(parent_directory_path)+"/"+Equipment_Control_name, QtCore.QSettings.IniFormat)
        self.setting_equipment.setIniCodec("UTF-8")#设置格式


        #实例化 串口通信的类
        self.Uart = Uart_Tool(self.Uart_TxFinish_Flag, self.Uart_RebackSignal, self.Rx_Array)

        #自定义信号绑定槽函数
        self.Uart_TxFinish_Flag.connect(self.Uart_TxFinish_Check)
        self.Uart_RebackSignal.connect(self.SerialPortA_RxDataRecord_SeLDone_cb)#回传Rx数据个数 和 是否打印信息的标志位

        #将事件绑定槽函数
        self.SerialPortA.activated.connect(self.SerialPortA_Select_cb)
        self.SerialPortA_OnOff.clicked.connect(self.SerialPortA_OnOff_cb)  
        self.SerialPortA_Sent.clicked.connect(self.SerialPortA_DirectSent_PrintRxData_cb)
        
        # #控制电源电压
        self.groupBox_Heater_VCC.clicked.connect(self.Heater_VCC_En)
        self.groupBox_DRV_VDR.clicked.connect(self.DRV_VDR_En)
        self.groupBox_DRV_VCC.clicked.connect(self.DRV_VCC_En)
        self.ReadDA_HeaterVCC.clicked.connect(lambda: self.STM32_DacRead(1, self.print_info_fast))
        self.ReadDA_DRV_VCC.clicked.connect(lambda: self.STM32_DacRead(2, self.print_info_fast))          
        self.ReadDA_DRV_VDR.clicked.connect(lambda: self.STM32_DacRead(3, self.print_info_fast))
        self.WrtDA_HeaterVCC.clicked.connect(lambda: self.STM32_DacWrite(1, self.print_info_fast))
        self.WrtDA_DRV_VCC.clicked.connect(lambda: self.STM32_DacWrite(2, self.print_info_fast))
        self.WrtDA_DRV_VDR.clicked.connect(lambda: self.STM32_DacWrite(3,self.print_info_fast))         
        self.Update_PwrReport.clicked.connect(lambda: self.PwrReport_Update( self.print_info_fast))
        self.CDM_Consumption_Update.clicked.connect(lambda: self.CDM_Consumption_calculate( self.print_info_fast))
        self.pushButton_PowerUp.clicked.connect(self.PowerUp_cb)
        self.pushButton_PowerOff.clicked.connect(self.PowerOff_cb)
        
        self.HeaterR_DirectRd.clicked.connect(self.HeaterR_DirectGet_cb)
        self.pushButton_DRV_Control.clicked.connect(self.DRVControl_cb)

        
        self.HeaterR_DirectWrt.clicked.connect(self.HeaterR_DirectSet_cb)


        #HeaterVCC DA控制值
        self.DaValue_HeaterVCC_buf = self.setting.value("setup_Power/DaValue_HeaterVCC")
        self.DaValue_HeaterVCC.setText(self.DaValue_HeaterVCC_buf)
        #DRV_VDR DA控制值
        self.DaValue_DRV_VDR_buf = self.setting.value("setup_Power/DaValue_DRV_VDR")
        self.DaValue_DRV_VDR.setText(self.DaValue_DRV_VDR_buf)
        #DRV_VCC DA控制值
        self.DaValue_DRV_VCC_buf = self.setting.value("setup_Power/DaValue_DRV_VCC")
        self.DaValue_DRV_VCC.setText(self.DaValue_DRV_VCC_buf)

        self.AdOffset_DRV_VDR = self.setting.value("setup_Power/AdOffset_DRV_VDR")
        self.AdOffset_DRV_VCC = self.setting.value("setup_Power/AdOffset_DRV_VCC")
        self.AdOffset_HeaterVCC = self.setting.value("setup_Power/AdOffset_HeaterVCC")


        self.setting_CDM.setValue('setup_HeaterR/Heater_Flag', True)#便于只是HeaterR是否已跟新
        self.setting_CDM.setValue('setup/DRV_Temperature_Flag', True)

        self.Rd_AllADC.clicked.connect(lambda:self.Rd_AllADC_cb(self.print_info_all))       

    #DRV Control             
    def DRVControl_cb(self):
        if self.SerialPort_CheckConnect() == True:     
            
            self.textBroswerPrintRealTime('启动DRVControl 子窗口')
            self.textBroswerPrintRealTime(self.Time_record()+'\n')
            
            self.DRV_Control_Pane_show = DRV_Control_Pane(self.DRV_Tx, self.Rx_Array)
            self.DRV_Tx.connect(self.SerialPortA_SentDrvCmd_RebackRxData_cb)
            self.DRV_Control_Pane_show.Drv_window_Close.connect(self.DRVControl_close_cb)
            
            self.DRV_Control_Pane_show.show()
            self.pushButton_DRV_Control.setEnabled(False)
            self.DRV_Control_Pane_show.textBrowser_DRVControl_PrintRealTime('DRVControl 子窗口 已打开')
    
    def DRVControl_close_cb(self):
            # print('DRVControl 子窗口 已关闭')
            self.textBroswerPrintRealTime('DRVControl 子窗口 已关闭')
            self.pushButton_DRV_Control.setEnabled(True)

    def Time_record(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+'  '
    # textBrowser实时打印信息
    def textBroswerPrintRealTime(self, text, show_flag = [1, True, False]):  

        self.LogPrint.emit(text, show_flag)

 
    #实时检测串口的工作状态
    def check_serial_ports(self,SerialPort_buf):

        # 电脑识别当前可用串口号  Identify SerialPort Number
        COM_List = list(serial.tools.list_ports.comports())
        if len(COM_List) == 0:
            self.textBroswerPrintRealTime('没有可用串口/NO SerialPort connect to PC')
        else:
            self.textBroswerPrintRealTime('当前可用串口信息/Current SerialPort Info:')
            for i in range(0, len(COM_List)):
                self.textBroswerPrintRealTime(str(COM_List[i]))

        # 将识别到的当前串口号列表，分别显示在所有需要选择串口进行连接的串口Qcombobox处 / show SerialPort_list in SerialPortA
            if len(COM_List) > 0:
                for i in range(0, len(COM_List)):
                    SerialPort_buf.addItem(COM_List[i].name)
    #串口选择
    def SerialPortA_Select_cb(self):
        # 打印 下拉框选中的内容
        num = self.SerialPortA.currentText()

        text = "SerialPortA Select %s" % num 
        text1 = "串口A选择%s " % num 
        self.textBroswerPrintRealTime(text+'/'+text1, self.print_info_all)
        
        self.SerialPortA_COM = num
        self.setting.setValue("setup_SerialPortA/SerialPortA_COM", num)
        # 串口初始化
        # self.SerialPortA_COM = self.setting.value("setup_SerialPortA/SerialPortA_COM")
        self.textBroswerPrintRealTime('SerialPortA_COM: '+str(self.SerialPortA_COM), self.print_info_fast)
        self.SerialPortA_Baud = self.setting.value("setup_SerialPortA/SerialPortA_Baud")
        self.textBroswerPrintRealTime('SerialPortA_Baud: '+str(self.SerialPortA_Baud), self.print_info_fast)
        self.SerialPortA_DataBit = self.setting.value("setup_SerialPortA/SerialPortA_DataBit")
        self.textBroswerPrintRealTime('SerialPortA_DataBit: '+str(self.SerialPortA_DataBit), self.print_info_fast)
        self.SerialPortA_Parity = self.setting.value("setup_SerialPortA/SerialPortA_Parity")
        self.textBroswerPrintRealTime('SerialPortA_Parity: '+str(self.SerialPortA_Parity), self.print_info_fast)
        self.SerialPortA_StopBit = self.setting.value("setup_SerialPortA/SerialPortA_StopBit")
        self.textBroswerPrintRealTime('SerialPortA_StopBit: '+str(self.SerialPortA_StopBit), self.print_info_fast)
        self.SerialPortA_Flow = self.setting.value("setup_SerialPortA/SerialPortA_Flow")
        self.textBroswerPrintRealTime('SerialPortA_Flow: '+str(self.SerialPortA_Flow), self.print_info_fast)                      
    #串口连接&关闭
    def SerialPortA_OnOff_cb(self):
        # 获取SerialPortA框中的当前内容进行判断
        self.SerialPortA_COM = self.SerialPortA.currentText()
        if self.SerialPortA_COM != '':
            self.SerialPortA_Select_cb()

        text = ''
        if self.SerialPortA_OnOff.text() == '连接/Connect' :
            # 先关闭接收线程,然后关闭串口，便于串口重新打开
            self.Uart.Uart_Rx_ThreadOver() 
            sleep(0.002)
            
            self.SerialPortA_Flag = self.Uart.SerialPort_Close()
            
            self.SerialPortA_OnOff.setText("connecting")
            sleep(0.01)
            self.textBroswerPrintRealTime('\nconnecting SerialPort...', self.print_info_fast)
            
            #打开串口
            self.SerialPortA_Flag = self.Uart.SerialPort_Open(self.SerialPortA_COM, self.SerialPortA_Baud)
            
            if self.SerialPortA_Flag == True :
                # text = 'SerialPortA '+'ConnectSuccess'+'/串口A'+'连接成功, '
                # self.SerialPortA_OnOff.setText("关闭/Disconnect")
                # self.SerialPortA.setEnabled(False)   # 串口号变为不可选择
                # self.label_SerialPort.setStyleSheet('background-color:rgb(0, 255, 0)')
                
                
            
                #电源状态判断: 板子已上电则再次打开GUI,电源上下点按键自己置位,否则保持待上电需操作上电按键
                buf = self.Power_Check()#返回值： True：则FW读取到数值为上电、False：则FW读取到数值为上电、'接收失败'：则FW未上电
                if  buf == True:
                    self.pushButton_PowerUp.setEnabled(False)
                    self.pushButton_PowerOff.setEnabled(True)
                    
                    #HeaterVCC DA控制值
                    DaValue_buf = self.STM32_DacRead(1,self.print_info_no)
                    self.DaValue_HeaterVCC.setText(DaValue_buf)
                    #DRV_VCC DA控制值
                    DaValue_buf = self.STM32_DacRead(2,self.print_info_no)
                    self.DaValue_DRV_VCC.setText(DaValue_buf)                         
                    #DRV_VDR DA控制值
                    DaValue_buf= self.STM32_DacRead(3,self.print_info_no)
                    self.DaValue_DRV_VDR.setText(DaValue_buf)
               
                                
                    self.setting.setValue("setup/SerialPortA_ConnectFlag", True)
                    text = 'The board is powered on!'

                    text = 'SerialPortA '+'ConnectSuccess'+'/串口A'+'连接成功, '
                    self.SerialPortA_OnOff.setText("关闭/Disconnect")
                    self.SerialPortA.setEnabled(False)   # 串口号变为不可选择
                    self.label_SerialPort.setStyleSheet('background-color:rgb(0, 255, 0)')


          
                elif buf == '接收失败':
                    text = 'Please check: whether the COM number is correct or whether the board hardware is work well, then try connecting again. '
                    # 先关闭接收线程,然后关闭串口
                    self.Uart.Uart_Rx_ThreadOver() 
                    sleep(0.002)

                    self.SerialPortA_Flag = self.Uart.SerialPort_Close()   
                    self.setting.setValue("setup/SerialPortA_ConnectFlag", False)
                    self.SerialPortA_OnOff.setText("连接/Connect")
                    self.label_SerialPort.setStyleSheet('background-color:rgb(255, 255, 255)')

                else: 
                    text = '\nThe board is not powered on: HeaterBiasVolt; DRV_VCC; DRV VDD.\n'
                    self.textBroswerPrintRealTime(text, self.print_info_fast)
                    
                    text = 'Initializing control voltage DAC_value... '
                    self.textBroswerPrintRealTime(text, self.print_info_fast)            
                    # 初始化三个电源的DAC值
                    self.DacValue_Buf = self.DaValue_HeaterVCC.text()
                    if len(self.DacValue_Buf.strip()) != 0:
                        self.DacValue = int(float(self.DacValue_Buf.strip())/self.STM32_ADC_VREF*4096)
                        DA_cmd = 'dac 1 '+ str(self.DacValue)
                        self.SerialPortA_SentCMD_SelPrintRxData_cb(DA_cmd, self.print_info_fast,self.DoneNum_0)                

                    self.DacValue_Buf = self.DaValue_DRV_VCC.text()
                    if len(self.DacValue_Buf.strip()) != 0:
                        self.DacValue = int(float(self.DacValue_Buf.strip())/self.STM32_ADC_VREF*4096)
                        DA_cmd = 'dac 2 '+ str(self.DacValue)
                        self.SerialPortA_SentCMD_SelPrintRxData_cb(DA_cmd, self.print_info_fast,self.DoneNum_0)     

                    self.DacValue_Buf = self.DaValue_DRV_VDR.text()
                    if len(self.DacValue_Buf.strip()) != 0:
                        self.DacValue = int(float(self.DacValue_Buf.strip())/self.STM32_ADC_VREF*4096)
                        DA_cmd = 'dac 3 '+ str(self.DacValue)
                        self.SerialPortA_SentCMD_SelPrintRxData_cb(DA_cmd, self.print_info_fast,self.DoneNum_0)
                    self.pushButton_PowerUp.setEnabled(True)
                    self.pushButton_PowerOff.setEnabled(False)    

                    self.setting.setValue("setup/SerialPortA_ConnectFlag", True)

                    text = 'SerialPortA '+'ConnectSuccess'+'/串口A'+'连接成功, '
                    self.SerialPortA_OnOff.setText("关闭/Disconnect")
                    self.SerialPortA.setEnabled(False)   # 串口号变为不可选择
                    self.label_SerialPort.setStyleSheet('background-color:rgb(0, 255, 0)')



            else:
                text = 'SerialPortA '+'ConnectFailed'+'/串口A'+'连接失败, '
                
                self.Uart.Uart_Rx_ThreadOver() 
                sleep(0.002)

                self.SerialPortA_Flag = self.Uart.SerialPort_Close()   
                self.setting.setValue("setup/SerialPortA_ConnectFlag", False)
                self.SerialPortA_OnOff.setText("连接/Connect")
                self.label_SerialPort.setStyleSheet('background-color:rgb(255, 255, 255)')
                             
            self.textBroswerPrintRealTime(text+self.Time_record()+'\n', self.print_info_all)
  


        elif self.SerialPortA_OnOff.text() == '关闭/Disconnect' and self.setting.value("setup/SerialPortA_ConnectFlag")==True:
            
            # 先关闭接收线程,然后关闭串口
            self.Uart.Uart_Rx_ThreadOver() 
            sleep(0.002)
            self.SerialPortA_Flag = self.Uart.SerialPort_Close()
            if self.SerialPortA_Flag == True:
                text = 'SerialPortA '+'CloseSuccess'+'/串口A'+'关闭成功, '
                self.SerialPortA.setEnabled(True)  # 串口号变为可选择
                self.SerialPortA_OnOff.setText("连接/Connect")
                self.setting.setValue("setup/SerialPortA_ConnectFlag", False)
                self.label_SerialPort.setStyleSheet('background-color:rgb(255, 255, 255)')
            else:
                text = 'SerialPortA '+'CloseFailed'+'/串口A'+'关闭失败, '
                self.setting.setValue("setup/SerialPortA_ConnectFlag", True)
            self.textBroswerPrintRealTime(text+self.Time_record(), self.print_info_all)
            self.pushButton_PowerUp.setEnabled(True)
            self.pushButton_PowerOff.setEnabled(True)
    #判断串口是否处于连接状态
    def SerialPort_CheckConnect(self):

        if self.SerialPortA_OnOff.text() == '连接/Connect':
            text = 'PleaseConnect SerialPortA/请先连接串口A, '
            QtWidgets.QMessageBox.information(self, "提示", text, QMessageBox.Ok | QMessageBox.Close)
        else: 
            return True
           
    #串口发送成功，自定义信号绑定该槽函数,判断 是否成功发送
    def Uart_TxFinish_Check(self, TxFlag, show_flag, DrvCmd_flag='', Tx_cmd = ''):
        
            if DrvCmd_flag == '':
                if show_flag[2] == True:
                    if TxFlag == True:
                        text = str(self.SerialPortA_COM)+" SendSucceed/"+str(self.SerialPortA_COM)+"串口A发送成功" 
                    else:
                        text =  str(self.SerialPortA_COM)+" SendFaild/"+str(self.SerialPortA_COM)+"串口A发送失败"     
                    self.textBroswerPrintRealTime(text, show_flag)#show_flag = list
                        
            elif DrvCmd_flag == 'DRV':#DrvCmd_flag == 'DRV':
                self.DRV_Control_Pane_show.Drv_TxFinish_flag.emit(Tx_cmd, TxFlag, show_flag)#发回去DRV函数   
    #使用串口指令框，直接发送数据
    def SerialPortA_DirectSent_PrintRxData_cb(self):
        # 判断串口是否已经连接
        if self.SerialPortA_OnOff.text() == '连接/Connect':
            text = 'Please Connect SerialPortA/请先连接串口A, '
            self.textBroswerPrintRealTime(text, self.print_info_all)
        else:
            
            self.Uart.Uart_Rx_ThreadStart()
   
            # 获取 SerialPortA_textEdit框中的内容
            textEdit = self.SerialPortA_textEdit.text()
            if textEdit == '':
                text = 'Please input commond/内容为空, 请输入指令, '
                self.textBroswerPrintRealTime(text)
            else:
                self.textBroswerPrintRealTime(textEdit)
                #触发自定义信号，启动Uart_Tx并判断 是否成功发送
                self.Uart.Tx_Signal.emit(textEdit, self.print_info_all, 'None', self.DoneNum_0)  #True：由线程触发 打印信息
                #Rx_data_Flag为True,则等待串口完成数据读取
                while self.Uart.Rx_data_Flag == True:
                    sleep(0.001)
                    pass             
        
                self.Uart.Uart_Rx_ThreadOver() 
                self.Uart.Rx_thread.join()
                # sleep(0.002)
                
    #函数调用串口，发送指令，并传输 是否打印Tx、RX信息的标志位
    def SerialPortA_SentCMD_SelPrintRxData_cb(self, cmd, show_flag = [1,True,False], DoneNum = 0):
        # 判断串口是否已经连接
        if self.SerialPort_CheckConnect() == True:

            self.Uart.Uart_Rx_ThreadStart()
            # sleep(0.002)
            
            self.textBroswerPrintRealTime(cmd, show_flag)
            self.Uart.Tx_Signal.emit(cmd, show_flag, 'None', DoneNum)#触发自定义信号,启动Uart_Tx并判断是否成功发送,1:返回信息进入数据进行保存
            #Rx_data_Flag为True,则等待串口完成数据读取
            while self.Uart.Rx_data_Flag == True:
                sleep(0.001)
                pass             
     
            self.Uart.Uart_Rx_ThreadOver() 
            self.Uart.Rx_thread.join()
            # sleep(0.002)
    #DRV调用串口                
    def SerialPortA_SentDrvCmd_RebackRxData_cb(self, cmd, show_flag = [1,True,False], DoneNum = 0):

        self.Uart.Uart_Rx_ThreadStart()
        # sleep(0.002)      
        self.Uart.Tx_DRV_Signal.emit(cmd, show_flag, 'DRV', DoneNum)#触发自定义信号,'DRV'代表DRV命令

        #Rx_data_Flag为True,则等待串口完成数据读取
        while self.Uart.Rx_data_Flag == True:
            sleep(0.001)
            pass            
        
        self.Uart.Uart_Rx_ThreadOver()   
        self.Uart.Rx_thread.join()  
        # sleep(0.002)
    #Rx数据完成后， 传递 数据个数/接收完成标志位/ 并自动判断是否打印Rx数据 
    def SerialPortA_RxDataRecord_SeLDone_cb(self, show_flag=[1,True,True], CmdType = 'None', DoneNum = 0, str_buf = ''):
        self.Rx_Array_ID = show_flag[0]
        if CmdType == 'None':
            if show_flag[1] == True:
                if DoneNum == 0:
                    #直接打印信息
                        self.SerialPortA_RxDataPrint_cb(self.Rx_Array_ID, self.Rx_Array, show_flag) 
                elif DoneNum ==  1:#adc读取
                        self.SerialPortA_RxDataPrint_cb(self.Rx_Array_ID, self.Rx_Array, show_flag)                 
                    
        elif CmdType == 'DRV':
            self.DRV_Control_Pane_show.watting_flag = False
            self.DRV_Control_Pane_show.Drv_RxData_Reback.emit(DoneNum, self.Rx_Array_ID,self.Rx_Array)#发回去DRV函数              
    #打印Rx数据 
    def SerialPortA_RxDataPrint_cb(self, num, array, show_flag = [1,True,True]):
        if show_flag[2] == True:
            self.textBroswerPrintRealTime('Receive '+str(num)+' words:',show_flag)
            for i in range (num):
                if i != num:
                    self.textBroswerPrintRealTime(array[i],show_flag)
            if show_flag[2] ==True:
                self.textBroswerPrintRealTime('')
        # for i in range (num):
        #     array[i] = ''     
              

    def Check_PwrDacValue(self, cmd, showinfo):#检查Power_DAC值

        #读取DAC值，判读是否为默认值0
        self.SerialPortA_SentCMD_SelPrintRxData_cb(cmd, showinfo)#发送指令进行PowerUp, 获取返回信息

        # 处理返回值，判断DAC初始值
        DacValue1 = ''
        DacValue2 = ''
        DacValue3 = ''
        #提取数字部分
        for char in self.Rx_Array[0]:
            if char.isdigit():
                DacValue1 += char  
        for char in self.Rx_Array[1]:
            if char.isdigit():
                DacValue2 += char
        for char in self.Rx_Array[2]:
            if char.isdigit():
                DacValue3 += char                    

        
        if int(DacValue1) == 0 or int(DacValue2) == 0 or int(DacValue3) == 0:
            return False
        else:
            if int(DacValue1) >1430 and int(DacValue2) >450 and int(DacValue3) > 2400:
                return True
            else:
                return False
   
    def PowerUp_cb(self):
        if self.SerialPort_CheckConnect() == True:
            Check_flag = self.Check_PwrDacValue('dac', self.print_info_no)#判断电源的DAC初始值是否已经配置
            # groupBox_Heater_VCC
            # groupBox_DRV_VDR
            # groupBox_DRV_VCC
            # EN 1:LDO_P5V_ENA
            # EN 2:N5V_ENA   
            # EN 3:DCDC_5P8V_ENA        
            # EN 4:Heater_VCC_ENA
            # EN 5:DRV_VDD_ENA
            # EN 6:DRV_VCC_ENA

            if Check_flag == True and self.groupBox_Heater_VCC.isChecked() == True \
                    and self.groupBox_DRV_VDR.isChecked() == True and self.groupBox_DRV_VCC.isChecked() == True:

                self.pushButton_PowerUp.setText("dong...\nPower Up ")#使能按钮text改变文字
                text = '\n板子上电中... / doing PowerUp... '
                self.textBroswerPrintRealTime(text+self.Time_record())
                # self.SerialPortA_SentCMD_SelPrintRxData_cb('pwr 1 1')
                # self.SerialPortA_SentCMD_SelPrintRxData_cb('pwr 2 1')
                # self.SerialPortA_SentCMD_SelPrintRxData_cb('pwr 4 1')
                self.SerialPortA_SentCMD_SelPrintRxData_cb('pwr 0 1')
                text = '板子上电完成! / PowerUp successed '
                self.textBroswerPrintRealTime(text+self.Time_record()+'\n')
                

                self.pushButton_PowerUp.setText("板子已上电\nBoard PowerOn")
                self.pushButton_PowerOff.setText("板子下电\nBoard PowerOff ")
                self.pushButton_PowerUp.setEnabled(False)
                self.pushButton_PowerOff.setEnabled(True)


            elif Check_flag == True and self.groupBox_Heater_VCC.isChecked() == True \
                    and self.groupBox_DRV_VDR.isChecked() == False and self.groupBox_DRV_VCC.isChecked() == False:
                
                text = '\n板子上电中... /doing PowerUp onlyHeater_VCC...'
                
                self.textBroswerPrintRealTime('\n'+text, self.print_info_fast)
                self.textBroswerPrintRealTime(self.Time_record())
                self.pushButton_PowerUp.setText("Power Up\ndong...")#使能按钮text改变显示

                self.SerialPortA_SentCMD_SelPrintRxData_cb('pwr 1 1', self.print_info_fast)
                self.SerialPortA_SentCMD_SelPrintRxData_cb('pwr 2 1', self.print_info_fast)
                self.SerialPortA_SentCMD_SelPrintRxData_cb('pwr 3 1', self.print_info_fast)
                self.SerialPortA_SentCMD_SelPrintRxData_cb('pwr 4 1', self.print_info_fast)

                self.pushButton_PowerUp.setText("板子上电\nBoard PowerUp")
                text = '\n只有Heater_VCC上电完成/Heater_VCC_PowerUp successed '
                
                self.textBroswerPrintRealTime(text)
                self.textBroswerPrintRealTime(self.Time_record())

                self.pushButton_PowerUp.setEnabled(False)
                self.pushButton_PowerOff.setEnabled(True)                
                             
            elif Check_flag == True and self.groupBox_DRV_VDR.isChecked() == False and self.groupBox_DRV_VCC.isChecked() == True:
                
                text = '\n板子上电失败/PowerUp failed\n DRV_VCC&VDR有上电时序的要求,不能单独只对其中一个上电'
                self.textBroswerPrintRealTime(text) 
                
                text = '如需关闭DRV VDD电源,可正常上电后再关闭VDR'
                self.textBroswerPrintRealTime(text)     
                self.textBroswerPrintRealTime(self.Time_record())           
                               
            elif Check_flag == True and self.groupBox_DRV_VDR.isChecked() == True and self.groupBox_DRV_VCC.isChecked() == False:
                
                text = '\n板子上电失败/PowerUp failed\n DRV_VCC&VDR有上电时序的要求,不能单独只对其中一个上电'
                self.textBroswerPrintRealTime(text) 
                
                text = '如需关闭DRV VDD电源,可正常上电后再关闭VDR'
                self.textBroswerPrintRealTime(text)     
                self.textBroswerPrintRealTime(self.Time_record())                  
            
            elif  Check_flag == False:
                text = '\n板子上电失败/PowerUp failed,请设置合适的电源DAC初始值 '
                
                self.textBroswerPrintRealTime(text + self.Time_record()) 
                
                text = 'Need: DAC1 ≥1.2; DAC2 ≥ 0.4; DAC3 ≥2;'
                
                self.textBroswerPrintRealTime(text + self.Time_record(), self.print_info_fast) 
    def PowerOff_cb(self):
        if self.SerialPort_CheckConnect() == True:
            self.pushButton_PowerOff.setText(" doing...\nBoard PowerOff ")
            
            
            text = "板子下电中... / PowerOff in progress. " 
            self.textBroswerPrintRealTime('\n'+text+self.Time_record())
            self.SerialPortA_SentCMD_SelPrintRxData_cb('Waitting...')
            self.SerialPortA_SentCMD_SelPrintRxData_cb('pwr 0 0',self.print_info_no)    
            text = "板子下电完成... / PowerOff Done. "
            self.textBroswerPrintRealTime(text+self.Time_record())
                      
            self.pushButton_PowerOff.setText("板子已下电\nBoard PowerOff ")
            self.pushButton_PowerUp.setText("板子上电\nBoard PowerUp ")
            self.pushButton_PowerUp.setEnabled(True)
            self.pushButton_PowerOff.setEnabled(False)
            
            self.setting.setValue("setup/Board_PowerUp_Flag", False)
    def Power_Check(self):#用于上下电的状态判断

        #更新 电压offset值
        self.AdOffset_DRV_VDR = self.setting.value("setup_Power/AdOffset_DRV_VDR")
        self.AdOffset_DRV_VCC = self.setting.value("setup_Power/AdOffset_DRV_VCC")
        self.AdOffset_HeaterVCC = self.setting.value("setup_Power/AdOffset_HeaterVCC")

        VCC_ADC = self.STM32_AdcRead(1, self.print_info_fast, self.DoneNum_0)

        #返回值不是数字，则是‘接收失败’，FW可能未上电
        if self.Rx_Array[0] != '接收失败':
            VDR_ADC = self.STM32_AdcRead(2, self.print_info_fast, self.DoneNum_0)   
            HeatherVCC_ADC = self.STM32_AdcRead(5, self.print_info_fast, self.DoneNum_0) 
            
            #增加只上Heater_VCC 或者全部上电 或者 只有HeatherVCC_ADC 和 DRV_VCC上电，其他情况不再允许
            if self.groupBox_Heater_VCC.isChecked() == True and self.groupBox_DRV_VCC.isChecked() == False and self.groupBox_DRV_VDR.isChecked() == False:   
                if float(HeatherVCC_ADC) >4.9:
                    text =  "当前只有Heater_VCC上电"
                    self.textBroswerPrintRealTime(text)
                    return True
            elif self.groupBox_Heater_VCC.isChecked() == True and self.groupBox_DRV_VCC.isChecked() == True and self.groupBox_DRV_VDR.isChecked() == True:
                if float(HeatherVCC_ADC) >4.9 and float(VDR_ADC) >2.5 and float(VCC_ADC) >= 2.85:
                    text =  "Heater_VCC、DRV_VCC、DRV_VDR 已经上电"
                    self.textBroswerPrintRealTime(text)
                    return True
            elif self.groupBox_Heater_VCC.isChecked() == True and self.groupBox_DRV_VCC.isChecked() == True and self.groupBox_DRV_VDR.isChecked() == False:
                if float(HeatherVCC_ADC) >4.9 and float(VDR_ADC) >0 and float(VCC_ADC) >= 2.85:
                    text =  "当前只有Heater_VCC 和 DRV_VCC上电"
                    self.textBroswerPrintRealTime(text)
                    return True
                
        else:
            return '接收失败'     
 
    def PwrReport_Update(self, show_flag=[1,True,False], N5V_Show = 0):#STM32读取电压、电流AD上报

        if self.SerialPort_CheckConnect() == True:
            if self.pushButton_PowerUp.isEnabled() == False:
                text = 'Update_PwrReport... '
                self.textBroswerPrintRealTime(text, show_flag)
                self.AdOffset_DRV_VDR = self.setting.value("setup_Power/AdOffset_DRV_VDR")
                self.AdOffset_DRV_VCC = self.setting.value("setup_Power/AdOffset_DRV_VCC")
                self.AdOffset_HeaterVCC = self.setting.value("setup_Power/AdOffset_HeaterVCC")

                self.STM32_AdcRead(1, show_flag)
                self.STM32_AdcRead(2, show_flag)
                self.STM32_AdcRead(3, show_flag)   
                self.STM32_AdcRead(4, show_flag)     
                self.STM32_AdcRead(5, show_flag)
                if N5V_Show==0:
                    self.STM32_AdcRead(6, show_flag) 

                text = 'Update_PwrReport Done!'
            else:
                text = '板子未上电! 请正常上电完成后,更新电压AD采样'
            self.textBroswerPrintRealTime(text, show_flag)
            self.textBroswerPrintRealTime(self.Time_record())
    def CDM_Consumption_calculate(self, show_flag):
        if self.SerialPort_CheckConnect() == True:   
            text = 'CDM_Consumption Update...'
            self.textBroswerPrintRealTime(text, show_flag)  

            self.PwrReport_Update(show_flag, 1)
            self.DRV_VCC_V = self.AdtoVolt_DRV_VCC.text()
            self.DRV_VDR_V = self.AdtoVolt_DRV_VDR.text()
            self.DRV_ICC_mA = self.DRV_ICC.text()
            self.DRV_IDD_mA = self.DRV_IDD.text()
            
            if float(self.DRV_IDD_mA) < 20 or float(self.DRV_ICC_mA) < 20:
                CDM_Consumption = '**'
                text = 'Please check Power and Update PwrReport! '
            else:
                CDM_Consumption = float(self.DRV_VCC_V)*float(self.DRV_ICC_mA)/1000+float(self.DRV_VDR_V)*float(self.DRV_IDD_mA)/1000
                text = 'CDM_Consumption Update Done! '
            self.CDM_Consumption.setText(str(CDM_Consumption)[0:4])
            self.textBroswerPrintRealTime(text+self.Time_record()+'\n\n',show_flag)   
    def Rd_AllADC_cb(self, show_flag = [1,True,False]):
        if self.pushButton_PowerUp.isEnabled() == False:
            self.SerialPortA_SentCMD_SelPrintRxData_cb('adc', show_flag)  
            t=0
            AdcValue=''
            for i in (self.Rx_Array[6:30]):
                AdcValue = ''
                t=t+1
                for char in i:
                    if char.isdigit():
                        AdcValue += char
                # print(AdcValue)
                if t<=12:
                    self.setting_CDM.setValue('setup_HeaterR/'+str(self.HeaterR_Curr_Name_list[t]), AdcValue)
                else:
                    self.setting_CDM.setValue('setup_HeaterR/'+str(self.HeaterR_Volt_Name_list[t-12]), AdcValue)
            if self.setting_CDM.value('setup_HeaterR/Heater_Flag') ==  False:        
                for i in range (12):
                    V_buf  = self.setting_CDM.value('setup_HeaterR/'+str(self.HeaterR_Volt_Name_list[i+1]))
                    I_buf  = self.setting_CDM.value('setup_HeaterR/'+str(self.HeaterR_Curr_Name_list[i+1]))
                    R_buf = self.STM32_AdValue_calculate(0,V_buf,2)/self.STM32_AdValue_calculate(0,I_buf,1)
                    self.setting_CDM.setValue('setup_HeaterR/'+str(self.HeaterR_Name_list[i+1]), str(R_buf*1000)[0:6])
                    
                self.setting_CDM.setValue('setup_HeaterR/Heater_Flag', True)
        else:
            text = '板子未上电! 请正常上电完成后,更新所有AD采样'
            self.textBroswerPrintRealTime(text)
            self.textBroswerPrintRealTime(self.Time_record())                   
    
    def Rd_AllADC_DrvTemperature_cb(self, show_flag = [1,True,False]):
        if self.pushButton_PowerUp.isEnabled() == False:
            self.SerialPortA_SentCMD_SelPrintRxData_cb('adc', show_flag)  
            t=0
            AdcValue=''
            buf = ''
            for i in (self.Rx_Array[6:30]):
                AdcValue = ''
                t=t+1
                for char in i:
                    if char.isdigit():
                        AdcValue += char
                # print(AdcValue)
                if t<=12:
                    self.setting_CDM.setValue('setup_HeaterR/'+str(self.HeaterR_Curr_Name_list[t]), AdcValue)
                else:
                    self.setting_CDM.setValue('setup_HeaterR/'+str(self.HeaterR_Volt_Name_list[t-12]), AdcValue)
            if self.setting_CDM.value('setup_HeaterR/Heater_Flag') ==  False:        
                for i in range (12):
                    V_buf  = self.setting_CDM.value('setup_HeaterR/'+str(self.HeaterR_Volt_Name_list[i+1]))
                    I_buf  = self.setting_CDM.value('setup_HeaterR/'+str(self.HeaterR_Curr_Name_list[i+1]))
                    R_buf = self.STM32_AdValue_calculate(0,V_buf,2)/self.STM32_AdValue_calculate(0,I_buf,1)
                    self.setting_CDM.setValue('setup_HeaterR/'+str(self.HeaterR_Name_list[i+1]), str(R_buf*1000)[0:6])
                self.setting_CDM.setValue('setup_HeaterR/Heater_Flag', True)
                
            if self.setting_CDM.value('setup/DRV_Temperature_Flag') ==  False and self.setting_CDM.value('setup/DRV_Temperature_SaveFlag') ==  True:     
                if self.DRV_Control_Pane_show != '':
                    buf = self.DRV_Control_Pane_show.DRV_TemperatureRead_Record_cb(self.print_info_no)
                    self.setting_CDM.setValue('setup/DRV_Temperature', buf)  
                    self.setting_CDM.setValue('setup/DRV_Temperature_Flag', True) 
                else:
                    self.textBroswerPrintRealTime('DRV_Temperature记录,需打开DRV_Control子窗口 更新读取一次DRV_INFO')
                                 
                
        else:
            text = '板子未上电! 请正常上电完成后,更新所有AD采样'
            self.textBroswerPrintRealTime(text)
            self.textBroswerPrintRealTime(self.Time_record())         
    
    
    #处理STM32 ADC值，包含各种放大倍数，返回值为Float类型
    def STM32_AdValue_calculate(self, ch, AdcValue, type=0):#type = 0:Power_Volt&ICC;type = 1:HeaterR_ICC;type = 2:HeaterR_Volt;
        if type == 0:
            if ch ==1 or ch ==2 or ch ==5:
                volt = int(AdcValue)/4096.0*self.STM32_ADC_VREF/10.0*30
            elif  ch ==3 or ch ==4:
                volt = int(AdcValue)/4096.0*self.STM32_ADC_VREF/200*300/50.0/0.1*1000            
            elif  ch ==6:
                volt = int(AdcValue)/4096*self.STM32_ADC_VREF*3-5.039
        elif  type == 1:
            # volt = int(AdcValue)/4096*self.STM32_ADC_VREF/20/2*1000
            volt = int(AdcValue)/4096*self.STM32_ADC_VREF/20/4*1000
        elif  type == 2:
            # volt = int(AdcValue)/4096*self.STM32_ADC_VREF/10*30
            volt = int(AdcValue)/4096*self.STM32_ADC_VREF/1*4.3
        return  float(volt)
    #STM32读AD值,返回值为电压或者电流            
    def STM32_AdcRead(self, ch, showinfo_flag = [1,True,False], DoneNum = 0):
        if self.SerialPort_CheckConnect() == True:
            
            text = ''
            self.calaValue = 0
            self.textBroswerPrintRealTime('读ADC...', showinfo_flag)
            cmd_text = 'adc '+str(ch)
            self.SerialPortA_SentCMD_SelPrintRxData_cb(cmd_text, showinfo_flag, DoneNum)      
 
            # 处理返回值，判断DAC初始值
            AdcValue = ''
            self.calaValue = ''
            
            #提取数字部分
            for char in str(self.Rx_Array[0]):
                if char.isdigit():
                    AdcValue += char

            try:
                if ch == 1:
                    self.calaValue = self.STM32_AdValue_calculate(ch, AdcValue)
                    if self.calaValue <= float(self.AdOffset_DRV_VCC):
                        self.calaValue = '0'
                    else:
                        self.calaValue = str( self.calaValue - float(self.AdOffset_DRV_VCC)  )[0:5]
                    self.AdtoVolt_DRV_VCC.setText(self.calaValue)# V
                    text = 'DRV_VCC:' + self.calaValue +'V' 
                if ch == 2:
                    self.calaValue = self.STM32_AdValue_calculate(ch, AdcValue)
                    if self.calaValue < float(self.AdOffset_DRV_VDR):
                        self.calaValue = '0'
                    else:
                        self.calaValue = str( self.calaValue - float(self.AdOffset_DRV_VDR))[0:5]
                    self.AdtoVolt_DRV_VDR.setText(self.calaValue) # V
                    text = 'DRV_VDR: '+ self.calaValue +'V' 
                if ch == 3:
                    self.calaValue = self.STM32_AdValue_calculate(ch, AdcValue)
                    if float(self.calaValue) < 5:
                        self.calaValue = '0'
                    else:
                        self.calaValue = str( self.calaValue )[0:5]
                        
                    self.DRV_ICC.setText(self.calaValue)# mA
                    text = 'ICC: '+ self.calaValue +'mA'
                if ch == 4:
                    self.calaValue = self.STM32_AdValue_calculate(ch, AdcValue)
                    if float(self.calaValue) < 5:
                        self.calaValue = '0'
                    else:
                        self.calaValue = str( self.calaValue )[0:5]
                    self.DRV_IDD.setText(self.calaValue)# mA 
                    text = 'IDD: '+str(self.calaValue)+'mA'
                if ch == 5:
                    self.calaValue = self.STM32_AdValue_calculate(ch, AdcValue)
                    if self.calaValue < float(self.AdOffset_HeaterVCC):
                        self.calaValue = '0'
                    else:
                        self.calaValue = str( self.calaValue - float(self.AdOffset_HeaterVCC))[0:5]
                    self.AdtoVolt_HeaterVCC.setText(self.calaValue)# V
                    text = 'HeaterVCC: '+ self.calaValue +'V'   
                if ch == 6:
                    self.calaValue = self.STM32_AdValue_calculate(ch, AdcValue)
                    if float(self.calaValue) > 0:
                        self.calaValue = '0'
                    else:
                        self.calaValue = str( self.calaValue )[0:5]
                    text = 'ADC_N5V_VCC: '+ self.calaValue +'V'  
                                    
                if ch >= 7 and  ch <= 18:#读取heaterR电流
                    self.calaValue = self.STM32_AdValue_calculate(ch, AdcValue, 1)
                    text = self.HeaterR_Curr_Name_list[ch-6] + ': ' + str(self.calaValue)[0:5]+'mA' #数组坐标 平移取数组元素
                if ch >= 19 and ch <= 30:#读取heaterR电压
                    self.calaValue = self.STM32_AdValue_calculate(ch, AdcValue, 2)
                    text = self.HeaterR_Volt_Name_list[ch-18] + ': ' + str(self.calaValue)[0:5]+'V'
                    
                self.textBroswerPrintRealTime(text, showinfo_flag)
            
                return self.calaValue
            except:
                self.textBroswerPrintRealTime('读取失败,请确认测试板的状态', showinfo_flag)
                return 0
   
    def STM32_DacWrite(self, ch, showinfo):#STM32写DA值
        if self.SerialPort_CheckConnect() == True:  
          
            self.textBroswerPrintRealTime('写DAC...', showinfo)
            self.DacValue_Buf = ''
            self.DacValue = 0

            if ch == 1:
                self.DacValue_Buf = self.DaValue_HeaterVCC.text()
            if ch == 2:
                self.DacValue_Buf = self.DaValue_DRV_VCC.text()
            if ch == 3:
                self.DacValue_Buf = self.DaValue_DRV_VDR.text()

            if len(self.DacValue_Buf.strip()) != 0:
                self.DacValue = round(float(self.DacValue_Buf.strip())/self.STM32_ADC_VREF*4096)

                if ch == 1:
                    DA_cmd = 'dac 1 '+ str(self.DacValue)
                if ch == 2:
                    DA_cmd = 'dac 2 '+ str(self.DacValue)
                if ch == 3:
                    DA_cmd = 'dac 3 '+ str(self.DacValue)
                self.SerialPortA_SentCMD_SelPrintRxData_cb(DA_cmd, showinfo)                
    
                
            else:
                QtWidgets.QMessageBox.information(self, "提示", '请输入正确的DA值', QMessageBox.Ok | QMessageBox.Close)
    def STM32_DacRead(self, ch, showinfo):#STM32读DA值
        if self.SerialPort_CheckConnect() == True:
            
            text = ''
            self.textBroswerPrintRealTime('读DAC...', showinfo)

            DA_cmd = 'dac'
            self.SerialPortA_SentCMD_SelPrintRxData_cb(DA_cmd, showinfo)  
 
            # 处理返回值，判断DAC初始值
            DacValue1 = ''
            DacValue2 = ''
            DacValue3 = ''
            #提取数字部分
            for char in self.Rx_Array[0]:
                if char.isdigit():
                    DacValue1 += char  

            for char in self.Rx_Array[1]:
                if char.isdigit():
                    DacValue2 += char

            for char in self.Rx_Array[2]:
                if char.isdigit():
                    DacValue3 += char                     

            if ch == 1:
                DacValue_Volt = str( round(int(DacValue1)/4096.0*self.STM32_ADC_VREF ,1) )
                self.DaValue_HeaterVCC.setText(DacValue_Volt)
                text = 'Dac1 DecValue: '+str(DacValue1)+', Dac1 Volt: '+DacValue_Volt
            if ch == 2:
                DacValue_Volt = str( round(int(DacValue2)/4096.0*self.STM32_ADC_VREF ,1) )
                self.DaValue_DRV_VCC.setText(DacValue_Volt)
                text = 'Dac2 DecValue: '+str(DacValue2)+', Dac2 Volt: '+DacValue_Volt
            if ch == 3:
                DacValue_Volt = str( round(int(DacValue3)/4096.0*self.STM32_ADC_VREF ,1) )
                self.DaValue_DRV_VDR.setText(DacValue_Volt) 
                text = 'Dac3 DecValue: '+str(DacValue3)+', Dac3 Volt: '+DacValue_Volt

            self.textBroswerPrintRealTime(text, showinfo)  
            return DacValue_Volt

    def Heater_VCC_En(self):
        if self.SerialPort_CheckConnect() == True:
            if self.groupBox_Heater_VCC.isChecked() == True:
                self.SerialPortA_SentCMD_SelPrintRxData_cb('pwr 4 1', self.print_info_fast)
            else:
                self.SerialPortA_SentCMD_SelPrintRxData_cb('pwr 4 0', self.print_info_fast)
    def DRV_VDR_En(self):
        if self.SerialPort_CheckConnect() == True:
            if self.groupBox_DRV_VDR.isChecked() == True:
                self.STM32_AdcRead(1)
                if float(self.AdtoVolt_DRV_VCC.text()) > 3:
                    self.SerialPortA_SentCMD_SelPrintRxData_cb('pwr 6 1', self.print_info_fast)
                    self.textBroswerPrintRealTime('VDR已上电')
                else:
                    self.groupBox_DRV_VDR.setChecked(False)
                    self.textBroswerPrintRealTime('请确保VCC已上电,再使能VDR上电')
            else:
                self.SerialPortA_SentCMD_SelPrintRxData_cb('pwr 6 0', self.print_info_fast)
                self.textBroswerPrintRealTime('VDR已下电')  
    def DRV_VCC_En(self):
        if self.SerialPort_CheckConnect() == True:
            if self.groupBox_DRV_VCC.isChecked() == True:
                self.SerialPortA_SentCMD_SelPrintRxData_cb('pwr 5 1', self.print_info_fast)
                self.textBroswerPrintRealTime('VCC已上电') 
            else:
                self.STM32_AdcRead(2)
                if float(self.AdtoVolt_DRV_VDR.text()) < 0.8:
                    self.SerialPortA_SentCMD_SelPrintRxData_cb('pwr 5 0', self.print_info_fast)
                    self.textBroswerPrintRealTime('VCC已下电')
                else:
                    self.groupBox_DRV_VCC.setChecked(True)
                    self.textBroswerPrintRealTime('请确保VDR已下电,再使能VCC下电')  
                    
    def HeaterR_DirectGet_cb(self):
        flag = True
        # 判断串口是否已经连接
        if self.SerialPort_CheckConnect() == True:
            self.textBroswerPrintRealTime('Doing HeaterR DirectGet')
            self.HeaterR_DirectRd.setEnabled(False)

            #使用STM32 ADC整体读取命令

            try:
                XI_HeaterRP_Curr = self.STM32_AdcRead(7, self.print_info_no,1)#heaterR 电流
                XI_HeaterRN_Curr = self.STM32_AdcRead(8, self.print_info_no,1)
                XI_HeaterRP_Volt = self.STM32_AdcRead(19, self.print_info_no,2)#heaterR 电压
                XI_HeaterRN_Volt = self.STM32_AdcRead(20, self.print_info_no,2)
                if XI_HeaterRP_Curr > 1:
                    self.XI_HeaterR_P.setText(str(XI_HeaterRP_Volt/XI_HeaterRP_Curr*1000)[0:5]) #R
                else:
                    self.XI_HeaterR_P.setText('0') #R
                if XI_HeaterRN_Curr > 1:    
                    self.XI_HeaterR_N.setText(str(XI_HeaterRN_Volt/XI_HeaterRN_Curr*1000)[0:5]) #R
                else:
                    self.XI_HeaterR_N.setText('0') #R
                self.textBroswerPrintRealTime('XI HeaterR已显示')

                XQ_HeaterRP_Curr= self.STM32_AdcRead(9, self.print_info_no,1)
                XQ_HeaterRN_Curr= self.STM32_AdcRead(10, self.print_info_no,1)
                XQ_HeaterRP_Volt= self.STM32_AdcRead(21, self.print_info_no,2)
                XQ_HeaterRN_Volt= self.STM32_AdcRead(22, self.print_info_no,2)
                if XQ_HeaterRP_Curr > 1: 
                    self.XQ_HeaterR_P.setText(str(XQ_HeaterRP_Volt/XQ_HeaterRP_Curr*1000)[0:5]) #
                else:
                    self.XQ_HeaterR_P.setText('0') #R
                if XQ_HeaterRN_Curr > 1:
                    self.XQ_HeaterR_N.setText(str(XQ_HeaterRN_Volt/XQ_HeaterRN_Curr*1000)[0:5])
                else:
                    self.XQ_HeaterR_N.setText('0')
                self.textBroswerPrintRealTime('XQ HeaterR已显示')

                XP_HeaterRP_Curr= self.STM32_AdcRead(15, self.print_info_no,1)
                XP_HeaterRN_Curr= self.STM32_AdcRead(16, self.print_info_no,1)
                XP_HeaterRP_Volt= self.STM32_AdcRead(27, self.print_info_no,2)
                XP_HeaterRN_Volt= self.STM32_AdcRead(28, self.print_info_no,2)
                if XP_HeaterRP_Curr > 1:                 
                    self.XP_HeaterR_P.setText(str(XP_HeaterRP_Volt/XP_HeaterRP_Curr*1000)[0:5]) #
                else:
                    self.XP_HeaterR_P.setText('0') #R
                if XP_HeaterRN_Curr > 1: 
                    self.XP_HeaterR_N.setText(str(XP_HeaterRN_Volt/XP_HeaterRN_Curr*1000)[0:5]) #
                else:
                    self.XP_HeaterR_N.setText('0') #R
                self.textBroswerPrintRealTime('XP HeaterR已显示')

                YI_HeaterRP_Curr= self.STM32_AdcRead(11, self.print_info_no,1)
                YI_HeaterRN_Curr= self.STM32_AdcRead(12, self.print_info_no,1)
                YI_HeaterRP_Volt= self.STM32_AdcRead(23, self.print_info_no,2)
                YI_HeaterRN_Volt= self.STM32_AdcRead(24, self.print_info_no,2)
                if YI_HeaterRP_Curr > 1: 
                    self.YI_HeaterR_P.setText(str(YI_HeaterRP_Volt/YI_HeaterRP_Curr*1000)[0:5]) #
                else:
                    self.YI_HeaterR_P.setText('0') #R
                if YI_HeaterRN_Curr > 1: 
                    self.YI_HeaterR_N.setText(str(YI_HeaterRN_Volt/YI_HeaterRN_Curr*1000)[0:5]) #
                else:
                    self.YI_HeaterR_N.setText('0') #R
                self.textBroswerPrintRealTime('YI HeaterR已显示')
                
                YQ_HeaterRP_Curr= self.STM32_AdcRead(13, self.print_info_no,1)
                YQ_HeaterRN_Curr= self.STM32_AdcRead(14, self.print_info_no,1)
                YQ_HeaterRP_Volt= self.STM32_AdcRead(25, self.print_info_no,2)
                YQ_HeaterRN_Volt= self.STM32_AdcRead(26, self.print_info_no,2)
                if YQ_HeaterRP_Curr > 1: 
                    self.YQ_HeaterR_P.setText(str(YQ_HeaterRP_Volt/YQ_HeaterRP_Curr*1000)[0:5]) #
                else:
                    self.YQ_HeaterR_P.setText('0') #R
                if YQ_HeaterRN_Curr > 1: 
                    self.YQ_HeaterR_N.setText(str(YQ_HeaterRN_Volt/YQ_HeaterRN_Curr*1000)[0:5]) #
                else:
                    self.YQ_HeaterR_N.setText('0') #R
                self.textBroswerPrintRealTime('YQ HeaterR已显示')
                
                YP_HeaterRP_Curr= self.STM32_AdcRead(17, self.print_info_no,1)
                YP_HeaterRN_Curr= self.STM32_AdcRead(18, self.print_info_no,1)
                YP_HeaterRP_Volt= self.STM32_AdcRead(29, self.print_info_no,2)
                YP_HeaterRN_Volt= self.STM32_AdcRead(30, self.print_info_no,2)     
                if YP_HeaterRP_Curr > 1:
                    self.YP_HeaterR_P.setText(str(YP_HeaterRP_Volt/YP_HeaterRP_Curr*1000)[0:5]) #
                else:
                    self.YP_HeaterR_P.setText('0') #R
                if YP_HeaterRN_Curr > 1:
                    self.YP_HeaterR_N.setText(str(YP_HeaterRN_Volt/YP_HeaterRN_Curr*1000)[0:5]) #
                else:
                    self.YP_HeaterR_N.setText('0') #R
                self.textBroswerPrintRealTime('YP HeaterR已显示')
                
                text = 'HeaterR DirectGet Done' 
            except:
                text = '读取失败,请检查'

                self.textBroswerPrintRealTime(text+self.Time_record())
                self.textBroswerPrintRealTime('')

            self.HeaterR_DirectRd.setEnabled(True)

            return 1

    def HeaterR_DirectSet_cb(self):
        text = '\nDoing HeaterR_DirectSet ' 
        # print(text)
        self.textBroswerPrintRealTime(text+self.Time_record())

        self.BUF_XI_HeaterRP = self.XI_HeaterR_P.text()
        self.setting.setValue("setup/BUF_XI_HeaterRP", self.BUF_XI_HeaterRP)
        self.BUF_XI_HeaterRN = self.XI_HeaterR_N.text()
        self.setting.setValue("setup/BUF_XI_HeaterRN", self.BUF_XI_HeaterRN)
        DA_cmd = 'SETR 0x1A '+ str(int(float(self.BUF_XI_HeaterRP)*10)) #由于STM32指令判断的格式 1A需加0x
        self.SerialPortA_SentCMD_SelPrintRxData_cb(DA_cmd, self.print_info_fast) 
        DA_cmd = 'SETR 0x1B '+ str(int(float(self.BUF_XI_HeaterRN)*10)) #由于STM32指令判断的格式 1A需加0x
        self.SerialPortA_SentCMD_SelPrintRxData_cb(DA_cmd, self.print_info_fast)

        self.BUF_XQ_HeaterRP = self.XQ_HeaterR_P.text()
        self.setting.setValue("setup/BUF_XQ_HeaterRP", self.BUF_XQ_HeaterRP)
        self.BUF_XQ_HeaterRN = self.XQ_HeaterR_N.text()
        self.setting.setValue("setup/BUF_XQ_HeaterRN", self.BUF_XQ_HeaterRN)
        DA_cmd = 'SETR 0x2A '+ str(int(float(self.BUF_XQ_HeaterRP)*10)) #由于STM32指令判断的格式 1A需加0x
        self.SerialPortA_SentCMD_SelPrintRxData_cb(DA_cmd, self.print_info_fast)
        DA_cmd = 'SETR 0x2B '+ str(int(float(self.BUF_XQ_HeaterRN)*10)) #由于STM32指令判断的格式 1A需加0x
        self.SerialPortA_SentCMD_SelPrintRxData_cb(DA_cmd, self.print_info_fast)

        self.BUF_YI_HeaterRP = self.YI_HeaterR_P.text()
        self.setting.setValue("setup/BUF_YI_HeaterRP", self.BUF_YI_HeaterRP)
        self.BUF_YI_HeaterRN = self.YI_HeaterR_N.text()
        self.setting.setValue("setup/BUF_YI_HeaterRN", self.BUF_YI_HeaterRN)
        DA_cmd = 'SETR 0x3A '+ str(int(float(self.BUF_YI_HeaterRP)*10)) #由于STM32指令判断的格式 1A需加0x
        self.SerialPortA_SentCMD_SelPrintRxData_cb(DA_cmd, self.print_info_fast)
        DA_cmd = 'SETR 0x3B '+ str(int(float(self.BUF_YI_HeaterRN)*10)) #由于STM32指令判断的格式 1A需加0x
        self.SerialPortA_SentCMD_SelPrintRxData_cb(DA_cmd, self.print_info_fast)

        self.BUF_YQ_HeaterRP = self.YQ_HeaterR_P.text()
        self.setting.setValue("setup/BUF_YQ_HeaterRP", self.BUF_YQ_HeaterRP)
        self.BUF_YQ_HeaterRN = self.YQ_HeaterR_N.text()
        self.setting.setValue("setup/BUF_YQ_HeaterRN", self.BUF_YQ_HeaterRN)
        DA_cmd = 'SETR 0x4A '+ str(int(float(self.BUF_YQ_HeaterRP)*10)) #由于STM32指令判断的格式 1A需加0x
        self.SerialPortA_SentCMD_SelPrintRxData_cb(DA_cmd, self.print_info_fast)
        DA_cmd = 'SETR 0x4B '+ str(int(float(self.BUF_YQ_HeaterRN)*10)) #由于STM32指令判断的格式 1A需加0x
        self.SerialPortA_SentCMD_SelPrintRxData_cb(DA_cmd, self.print_info_fast)

        self.BUF_XP_HeaterRP = self.XP_HeaterR_P.text()
        self.setting.setValue("setup/BUF_XP_HeaterRP", self.BUF_XP_HeaterRP)
        self.BUF_XP_HeaterRN = self.XP_HeaterR_N.text()
        self.setting.setValue("setup/BUF_XP_HeaterRN", self.BUF_XP_HeaterRN)
        DA_cmd = 'SETR 0x5A '+ str(int(float(self.BUF_XP_HeaterRP)*10)) #由于STM32指令判断的格式 1A需加0x
        self.SerialPortA_SentCMD_SelPrintRxData_cb(DA_cmd, self.print_info_fast)
        DA_cmd = 'SETR 0x5B '+ str(int(float(self.BUF_XP_HeaterRN)*10)) #由于STM32指令判断的格式 1A需加0x
        self.SerialPortA_SentCMD_SelPrintRxData_cb(DA_cmd, self.print_info_fast)


        self.BUF_YP_HeaterRP = self.YP_HeaterR_P.text()
        self.setting.setValue("setup/BUF_YP_HeaterRP", self.BUF_YP_HeaterRP)
        self.BUF_YP_HeaterRN = self.YP_HeaterR_N.text()
        self.setting.setValue("setup/BUF_YP_HeaterRN", self.BUF_YP_HeaterRN)       
        DA_cmd = 'SETR 0x6A '+ str(int(float(self.BUF_YP_HeaterRP)*10)) #由于STM32指令判断的格式 1A需加0x
        self.SerialPortA_SentCMD_SelPrintRxData_cb(DA_cmd, self.print_info_fast)
        DA_cmd = 'SETR 0x6B '+ str(int(float(self.BUF_YP_HeaterRN)*10)) #由于STM32指令判断的格式 1A需加0x
        self.SerialPortA_SentCMD_SelPrintRxData_cb(DA_cmd, self.print_info_fast)        

        text = 'HeaterR_DirectSet Done' 
        # print(text)
        self.textBroswerPrintRealTime(text+self.Time_record())
        return 1



if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    window = CDM_GUI_Pane()
    # window.exit_signal.connect(lambda:print('cc'))
    # window.register_signal.connect(lambda a,p : print(a,p))

    window.show()

    window.check_serial_ports(window.SerialPortA)

    sys.exit(app.exec_())
