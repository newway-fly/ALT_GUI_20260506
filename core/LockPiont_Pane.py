import sys,datetime,re,csv,os,math
from PyQt5 import QtWidgets,QtCore
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import pyqtSignal
# sys.path.append(os.getcwd())
from utils.Ui_CDM_LockPiont import Ui_Form
from utils.UartB import Uart_Tool
from time import sleep
from core.LongTimeCmd_QThread import SendCmd_SelPrint_Waitting_CheckDone_cb
import numpy as np

class LockPiont_Pane(QtWidgets.QWidget,Ui_Form):

    # Uart_TxFinish_Flag = pyqtSignal(str, bool, list)#串口 tx信息、发送成功标志位、是否打印标志位
    
    Uart_RebackSignal = pyqtSignal( int, list , list)#串口回传的信息(短耗时指令)：个数 & 数据接收完成的标志 & 是否由线程触发->打印信息
    LogPrint = pyqtSignal(str, list)
    RefreshHeaterR_STM32 = pyqtSignal()
    Reback_AdcData = pyqtSignal(str,str)
    Call_PowerMeter = pyqtSignal(bool)
    
    def __init__(self,parent=None,*args,**kwargs):#该类一旦实例化，第一时间执行的内容
        super().__init__(parent,*args,**kwargs)
        #上面直接继承父类QtWidgets.QWidget，会覆盖_rc的背景图，增加这句命令即可
        # self.setAttribute(Qt.WA_StyledBackground, True)
        self.setupUi(self)
        
        self.Number_channel_list =  ['',   1,   2,   3,   4,   5,   6,  10] 
        self.Name_channel_list =    ['','XI','XQ','YI','YQ','XP','YP','BaisAmpVolt']
        self.DaShow_channel_list = ['',self.DA_XI,self.DA_XQ,self.DA_YI,self.DA_YQ,self.DA_XP,self.DA_YP]
        self.DaRead_channel_list = ['',self.DA_XI_Read,self.DA_XQ_Read,self.DA_YI_Read,self.DA_YQ_Read,self.DA_XP_Read,self.DA_YP_Read]
        self.DaWrite_channel_list = ['',self.DA_XI_Write,self.DA_XQ_Write,self.DA_YI_Write,self.DA_YQ_Write,self.DA_XP_Write,self.DA_YP_Write,
                                     self.EN_PushPull_Volt_5V,self.EN_PushPull_Volt_6V5]
        self.VerticalSlider_channel_list = ['',self.VerticalSlider_XI,self.VerticalSlider_XQ,
                                                    self.VerticalSlider_YI,self.VerticalSlider_YQ,
                                                        self.VerticalSlider_XP,self.VerticalSlider_YP]
        self.Volt_LCDNumber_channel_list = ['',self.XI_Volt_LCDNumber,self.XQ_Volt_LCDNumber,
                                                    self.YI_Volt_LCDNumber,self.YQ_Volt_LCDNumber,
                                                        self.XP_Volt_LCDNumber,self.YP_Volt_LCDNumber]        

        self.LockPoint_NNQ_channel_list = ['',self.LockPoint_NNQ_XI,self.LockPoint_NNQ_XQ,self.LockPoint_NNQ_YI,self.LockPoint_NNQ_YQ,
                                                self.LockPoint_NNQ_XP,self.LockPoint_NNQ_YP]
        self.FindPoint_NNQ_channel_list = ['',self.FindPoint_NNQ_XI,self.FindPoint_NNQ_XQ,self.FindPoint_NNQ_YI,self.FindPoint_NNQ_YQ,
                                                self.FindPoint_NNQ_XP,self.FindPoint_NNQ_YP]
        self.HeaterR_Name_list = ['','XI_HeaterR_P','XI_HeaterR_N','XQ_HeaterR_P','XQ_HeaterR_N',
                                     'YI_HeaterR_P','YI_HeaterR_N','YQ_HeaterR_P','YQ_HeaterR_N',
                                     'XP_HeaterR_P','XP_HeaterR_N','YP_HeaterR_P','YP_HeaterR_N']     
        
        
        self.V_REF = 3.378
        self.Lock_TimeStart = ''
        self.Lock_TimeOver = ''
        self.FindPoint_TimeStart = ''
        self.FindPoint_TimeOver = '' 
        
        self.FindPoint_Record_length = 30
        
        self.Action_Num_ID = 0
        self.Rx_Array = ['']*30             #传递串口的Rx数据
        self.Rx_Array_buf= ['']*30          #传递串口的Rx数据
        self.PushPull_BiasAmpVolt = '07EA'
        # self.ALL_Lock_Flag = False
        
        self.CDM_T0_Value = ''
        self.CDM_WL0_Value = ''

        self.print_info_all = [2, True, True]
        self.print_info_fast = [2, True, False]
        self.print_info_no = [2, False, False]    
        # self.LockingFlag_False = False
        self.DoLocking_Flag = False
        self.CalibrateLocking_Flag = False
        
        
        self.BiasPoint_Mode = 0  #0=MinMinQuad; 1=MaxMaxMax
        self.LockPoint_cycle = 0
        
        self.Action_Num_Normal = 0

        self.Action_Num_FindPoint           = 1000#FindPoint
        self.Action_Num_PhAgainFindPoint    = 1001#PhaseAgain_FindPoint 
        self.Action_Num_IQAlignment         = 1002#IQAlignment
        self.Action_Num_IQLock              = 1003#IQLock
        
        self.Action_Num_FindPointRecrodSave = 1021# FindPoint saveData
        
        self.Action_Num_XY_Lock             = 1030# XY LOCK
        self.Action_Num_LockCalibration     = 1031# Deri_Cala

        
        
        # 设置串口配置文件的路径 加载内容
        self.setting = QtCore.QSettings("./data/config_Board.ini", QtCore.QSettings.IniFormat)
        self.setting.setIniCodec("UTF-8")#设置格式
        # 设置CDM配置文件的路径 加载内容
        self.setting_CDM = QtCore.QSettings("./data/config_CDM.ini", QtCore.QSettings.IniFormat)
        self.setting_CDM .setIniCodec("UTF-8")#设置格式

        self.SerialPortA_ConnectFlag = self.setting.value("setup/SerialPortA_ConnectFlag")
        self.setting.setValue("setup_SerialPortB/Flag_Stop",True)
        
        self.SerialPortB_Baud = self.setting.value("setup_SerialPortB/SerialPortB_COM")
        self.SerialPortB.addItem(self.setting.value("setup_SerialPortB/SerialPortB_COM"))

        # Equipment_Control_name = "Equipment_Control_V3.6/data/setting_equipment.ini"
        Equipment_Control_name = str(self.setting.value("directory_path/Equipment_Control_name"))+"/data/setting_equipment.ini"
       
        #映射到setting_equipment.ini
        parent_directory_path = self.setting.value("directory_path/parent_directory_path")
        self.setting_equipment = QtCore.QSettings(str(parent_directory_path)+"/"+str(Equipment_Control_name), QtCore.QSettings.IniFormat)
        self.setting_equipment.setIniCodec("UTF-8")#设置格式
        
        self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st", True)

        self.LockPoint_Run.setEnabled(True) 
        self.LockPoint_Stop.setEnabled(False)  

        self.LongTimeCmd_QThread = SendCmd_SelPrint_Waitting_CheckDone_cb(self.LogPrint,self.Rx_Array) 
        self.Uart = Uart_Tool(self.LongTimeCmd_QThread.Uart_TxFinish_Flag,  self.Uart_RebackSignal,
                              self.LongTimeCmd_QThread.Uart_RxCheckTx_Signal, self.LongTimeCmd_QThread.Uart_Reback_QThreadFinish_Signal, self.Rx_Array)

        self.LongTimeCmd_QThread.Uart_TxCmd_Flag.connect(self.Uart.Uart_Tx)    
        self.LongTimeCmd_QThread.Refresh_6ch_HeaterDA_Flag.connect(self.Refresh_6ch_HeaterDA)  
        self.LongTimeCmd_QThread.COM_Settings.connect(self.Refresh_COM_settings)
        self.LongTimeCmd_QThread.Trigger_Uart_StartFlag.connect(self.Triggle_Uart_QThreadstart)
        self.LongTimeCmd_QThread.Trigger_Uart_StoptFlag.connect(self.Triggle_Uart_QThreadstop)
        self.LongTimeCmd_QThread.Trigger_LockStop.connect(self.LockPoint_StopDone_cb)
        self.LongTimeCmd_QThread.Trigger_LockCycle_show.connect(self.LockPoint_cycle_show)
        self.LongTimeCmd_QThread.Trigger_LockInfo_show.connect(self.LockPoint_Info_show)
        self.LongTimeCmd_QThread.FindPoint_OverTime.connect(self.FindPoint_Timecalculate_cb)
        self.LongTimeCmd_QThread.Trigger_Uart_ClearBuffer.connect(self.COM_ClearBuffer)
        self.LongTimeCmd_QThread.Trigger_Calibrate_X_IQ_Loop.connect(self.Calibrate_X_IQ_DitherAmp_cb)
        self.LongTimeCmd_QThread.Trigger_Calibrate_Y_IQ_Loop.connect(self.Calibrate_Y_IQ_DitherAmp_cb)
        self.LongTimeCmd_QThread.Trigger_Calibrate_XP_Loop.connect(self.Calibrate_XP_DitherAmp_cb)
        self.LongTimeCmd_QThread.Trigger_Calibrate_YP_Loop.connect(self.Calibrate_YP_DitherAmp_cb)


        self.LongTimeCmd_QThread.Trigger_Call_PowerMeter.connect(self.Call_PowerMeter_cb)
        
        #短耗时 指令回调使用
        self.Uart_RebackSignal.connect(self.SerialPortA_RxDataRecord_SeLDone_cb)
        self.LongTimeCmd_QThread.Trigger_Refresh_HeaterR.connect(self.Refresh_HeaterR)
        
        

        self.SerialPortB_OnOff.clicked.connect(self.SerialPort_OnOff_cb)
        self.SerialPortB.activated.connect(self.SerialPortB_Select_cb)
        self.SerialPortB_Send.clicked.connect(lambda:self.SerialPortB_DirectSend_PrintTxRxData_cb(self.print_info_all))
        self.SerialPortB_Send_7844.clicked.connect(self.AdcRead_410_cb)
        
        #HeaterDA 读
        self.DaRead_channel_list[1].clicked.connect(lambda:self.HeaterDa_ReadHex_cb(1,self.Action_Num_Normal,self.print_info_fast))#XI
        self.DaRead_channel_list[2].clicked.connect(lambda:self.HeaterDa_ReadHex_cb(2,self.Action_Num_Normal,self.print_info_fast))#XQ
        self.DaRead_channel_list[3].clicked.connect(lambda:self.HeaterDa_ReadHex_cb(3,self.Action_Num_Normal,self.print_info_fast))#YI
        self.DaRead_channel_list[4].clicked.connect(lambda:self.HeaterDa_ReadHex_cb(4,self.Action_Num_Normal,self.print_info_fast))#YQ
        self.DaRead_channel_list[5].clicked.connect(lambda:self.HeaterDa_ReadHex_cb(5,self.Action_Num_Normal,self.print_info_fast))#XP
        self.DaRead_channel_list[6].clicked.connect(lambda:self.HeaterDa_ReadHex_cb(6,self.Action_Num_Normal,self.print_info_fast))#YP
        #HeaterDA 写
        self.DaWrite_channel_list[1].clicked.connect(lambda:self.HeaterDa_WriteHex_cb(1,self.Action_Num_Normal,self.print_info_fast))#XI
        self.DaWrite_channel_list[2].clicked.connect(lambda:self.HeaterDa_WriteHex_cb(2,self.Action_Num_Normal,self.print_info_fast))#XQ
        self.DaWrite_channel_list[3].clicked.connect(lambda:self.HeaterDa_WriteHex_cb(3,self.Action_Num_Normal,self.print_info_fast))#YI
        self.DaWrite_channel_list[4].clicked.connect(lambda:self.HeaterDa_WriteHex_cb(4,self.Action_Num_Normal,self.print_info_fast))#YQ
        self.DaWrite_channel_list[5].clicked.connect(lambda:self.HeaterDa_WriteHex_cb(5,self.Action_Num_Normal,self.print_info_fast))#XP
        self.DaWrite_channel_list[6].clicked.connect(lambda:self.HeaterDa_WriteHex_cb(6,self.Action_Num_Normal,self.print_info_fast))#YP        
        self.DaWrite_channel_list[7].clicked.connect(lambda:self.BiasAmpl_Rd_Wrt('Wrt',  5, self.Action_Num_Normal, self.print_info_fast))#5V
        self.DaWrite_channel_list[8].clicked.connect(lambda:self.BiasAmpl_Rd_Wrt('Wrt',6.5, self.Action_Num_Normal, self.print_info_fast))#6.5V 
        
        # self.FindPoint_CalPpi_Rd.clicked.connect(self.FindPoint_CalPpi_Rd_cb)   
        # self.FindPoint_CalPpi_Set.clicked.connect(self.FindPoint_CalPpi_Set_cb)           
        
        self.FindPoint.clicked.connect(self.FindPoint_cb)
        self.NNQ_Record_Save.clicked.connect(self.NNQ_Record_Save_cb)    
        self.LockPoint_NNQRecord_Read.clicked.connect(self.LockPoint_NNQRecord_Read_cb)
        self.LockPoint_NNQRecord_Set.clicked.connect(self.LockPoint_NNQRecord_Set_cb)   
        self.FindPoint_NNQRecord_Read.clicked.connect(self.FindPoint_NNQRecord_Read_cb)
        
        self.EXPD_AligPoint_Rd.clicked.connect(lambda:self.EXPD_AligPoint_Rd_cb(self.print_info_fast))   
        self.EXPD_AligPoint_Set.clicked.connect(lambda:self.EXPD_AligPoint_Set_cb(self.print_info_fast))
        self.EXPD_IQLockPoint_RefVolt_Rd.clicked.connect(lambda:self.EXPD_IQLockPoint_RefVolt_Rd_cb(self.print_info_fast))
        self.EXPD_IQLockPoint_RefVolt_Set.clicked.connect(lambda:self.EXPD_IQLockPoint_RefVolt_Set_cb(self.print_info_fast))
        self.EXPD_IQLockThreshold_Rd.clicked.connect(lambda:self.EXPD_IQLockThreshold_Rd_cb(self.print_info_fast))
        self.EXPD_IQLockThreshold_Set.clicked.connect(lambda:self.EXPD_IQLockThreshold_Set_cb(self.print_info_fast))
        self.EXPD_IQLock_Alignemet.clicked.connect(self.EXPD_IQLock_Alignemet_cb)
                
        self.XI_LockDither_Rd.clicked.connect(lambda:self.XI_LockDither_Rd_cb())   
        self.XI_LockDither_Set.clicked.connect(lambda:self.XI_LockDither_Set_cb(0,0))   
        self.XQ_LockDither_Rd.clicked.connect(lambda:self.XQ_LockDither_Rd_cb())   
        self.XQ_LockDither_Set.clicked.connect(lambda:self.XQ_LockDither_Set_cb(0,0))    
        self.YI_LockDither_Rd.clicked.connect(lambda:self.YI_LockDither_Rd_cb())   
        self.YI_LockDither_Set.clicked.connect(lambda:self.YI_LockDither_Set_cb(0,0))  
        self.YQ_LockDither_Rd.clicked.connect(lambda:self.YQ_LockDither_Rd_cb())   
        self.YQ_LockDither_Set.clicked.connect(lambda:self.YQ_LockDither_Set_cb(0,0))           
        self.XPhaseDither_Rd.clicked.connect(lambda:self.XP_LockDither_Rd_cb())   
        self.XPhaseDither_Set.clicked.connect(lambda:self.XP_LockDither_Set_cb(0,0,0))  
        self.YPhaseDither_Rd.clicked.connect(lambda:self.YP_LockDither_Rd_cb())   
        self.YPhaseDither_Set.clicked.connect(lambda:self.YP_LockDither_Set_cb(0,0,0))           

        self.XI_FirstDeri_Do.clicked.connect(self.XI_FirdtDeri_Do_cb)
        self.XQ_FirstDeri_Do.clicked.connect(self.XQ_FirdtDeri_Do_cb)
        self.YI_FirstDeri_Do.clicked.connect(self.YI_FirdtDeri_Do_cb)
        self.YQ_FirstDeri_Do.clicked.connect(self.YQ_FirdtDeri_Do_cb)
        self.XP_SecondDeri_Do.clicked.connect(self.XP_SecondDeri_Do_cb)
        self.YP_SecondDeri_Do.clicked.connect(self.YP_SecondDeri_Do_cb)
        
        
        self.XI_FirstDeri_Rd.clicked.connect(lambda:self.XI_FirdtDeri_Rd_cb(self.print_info_fast))  
        self.XQ_FirstDeri_Rd.clicked.connect(lambda:self.XQ_FirdtDeri_Rd_cb(self.print_info_fast))             
        self.YI_FirstDeri_Rd.clicked.connect(lambda:self.YI_FirdtDeri_Rd_cb(self.print_info_fast))            
        self.YQ_FirstDeri_Rd.clicked.connect(lambda:self.YQ_FirdtDeri_Rd_cb(self.print_info_fast)) 
        self.XP_SecondDeri_Rd.clicked.connect(lambda:self.XP_SecondDeri_Rd_cb(self.print_info_fast))
        self.YP_SecondDeri_Rd.clicked.connect(lambda:self.YP_SecondDeri_Rd_cb(self.print_info_fast))#
        self.XI_LockCalibration.clicked.connect(self.XI_LockCalibration_cb)
        self.XQ_LockCalibration.clicked.connect(self.XQ_LockCalibration_cb)
        self.XP_LockCalibration.clicked.connect(self.XP_LockCalibration_cb)
        self.YI_LockCalibration.clicked.connect(self.YI_LockCalibration_cb)
        self.YQ_LockCalibration.clicked.connect(self.YQ_LockCalibration_cb)
        self.YP_LockCalibration.clicked.connect(self.YP_LockCalibration_cb)
        
        self.XP_LockingThreshold_Rd.clicked.connect(self.XP_LockingThreshold_Rd_cb)
        self.YP_LockingThreshold_Rd.clicked.connect(self.YP_LockingThreshold_Rd_cb)   
        self.XP_LockingThreshold_Set.clicked.connect(self.XP_LockingThreshold_Set_cb) 
        self.YP_LockingThreshold_Set.clicked.connect(self.YP_LockingThreshold_Set_cb)
        self.FindPoint_Record_Save.clicked.connect(self.FindPoint_RecordSave_cb)
        self.PhaseAgain_Findpoint.clicked.connect(self.PhaseAgain_Findpoint_cb)
        self.LockPoint_Run.clicked.connect(self.LockingPoint_Run_cb)
        self.LockPoint_Stop.clicked.connect(self.LockPoint_Stop_cb)
        self.CDM_T_WL_Save.clicked.connect(self.CDM_T_WL_Save_cb)
        self.CDM_T_WL_Update.clicked.connect(self.update_WL_Temperature)
        self.CDM_SN_Save.clicked.connect(self.CDM_SN_Save_cb)

        self.Lock_MinMinQuad_EN.clicked.connect(lambda:self.set_BiasPiont_Mode_cb(0))        
        self.Lock_MaxMaxMax_EN.clicked.connect(lambda:self.set_BiasPiont_Mode_cb(1))

        
        self.Calibrate_X_IQ_DitherAmp.clicked.connect(self.Calibrate_X_IQ_DitherAmp_cb)
        self.Calibrate_Y_IQ_DitherAmp.clicked.connect(self.Calibrate_Y_IQ_DitherAmp_cb)
        self.Calibrate_XP_DitherAmp.clicked.connect(self.Calibrate_XP_DitherAmp_cb)
        self.Calibrate_YP_DitherAmp.clicked.connect(self.Calibrate_YP_DitherAmp_cb)
        
        
        
        self.BiasControl_PushPull_En.clicked.connect(lambda:self.BiasControl_SelectMode_cb('PushPull'))
        self.BiasControl_P_arm_En.clicked.connect(lambda:self.BiasControl_SelectMode_cb('P_arm'))
        self.BiasControl_N_arm_En.clicked.connect(lambda:self.BiasControl_SelectMode_cb('N_arm'))

        self.CDM_SN_buf = self.setting_CDM.value("setup/CDM_SN")
        self.CDM_SN.setText(str(self.CDM_SN_buf)) 
        self.CDM_T0_buf = self.setting_CDM.value("setup/T0")
        self.CDM_T0.setText(str(self.CDM_T0_buf)) 
        self.CDM_WL0_buf = round(float(self.setting_CDM.value("setup/WL0")),1)
        self.CDM_WL0.setText(str(self.CDM_WL0_buf)) 
        
        

    # textBrowser实时打印信息, 需要窗口之间传输信息
    def textBroswerPrintRealTime(self, text = '', show_flag = [2,True,False]):  
        self.LogPrint.emit(text, show_flag)

    #串口选择
    def SerialPortB_Select_cb(self):
        # 打印 下拉框选中的内容
        num = self.SerialPortB.currentText()
        text = 'SerialPortB'+" Select %s" % num 
        text1 = "串口B选择了%s, " % num 
        self.textBroswerPrintRealTime(text+'/'+text1+self.Time_text())
        # 串口信息
        self.SerialPortB_COM = num
        self.setting.setValue("setup_SerialPortB/SerialPortB_COM", num)  
        
        # 串口初始化
        # self.SerialPortB_COM = self.setting.value("setup_SerialPortB/SerialPortB_COM")
        # self.textBroswerPrintRealTime('SerialPortB_COM: '+str(self.SerialPortB_COM))
        self.SerialPortB_Baud = self.setting.value("setup_SerialPortB/SerialPortB_Baud")
        self.textBroswerPrintRealTime('SerialPortB_Baud: '+str(self.SerialPortB_Baud))
        self.SerialPortB_DataBit = self.setting.value("setup_SerialPortB/SerialPortB_DataBit")
        self.textBroswerPrintRealTime('SerialPortB_DataBit: '+str(self.SerialPortB_DataBit))
        self.SerialPortB_Parity = self.setting.value("setup_SerialPortB/SerialPortB_Parity")
        self.textBroswerPrintRealTime('SerialPortB_Parity: '+str(self.SerialPortB_Parity))
        self.SerialPortB_StopBit = self.setting.value("setup_SerialPortB/SerialPortB_StopBit")
        self.textBroswerPrintRealTime('SerialPortB_StopBit: '+str(self.SerialPortB_StopBit))
        self.SerialPortB_Flow = self.setting.value("setup_SerialPortB/SerialPortB_Flow")
        self.textBroswerPrintRealTime('SerialPortB_Flow: '+str(self.SerialPortB_Flow))              
    #串口连接&关闭
    def SerialPort_OnOff_cb(self):
        # 获取SerialPortB框中的当前内容进行判断
        num = self.SerialPortB.currentText()
        if num != '':
           self.SerialPortB_Select_cb() 
   
        self.SerialPortA_ConnectFlag = self.setting.value("setup/SerialPortA_ConnectFlag")
        
        if self.SerialPortB_OnOff.text() == '连接/Connect' and  self.SerialPortA_ConnectFlag == True:
            # 先关闭接收线程,然后关闭串口，便于串口重新打开
            self.Uart.Stop()
            sleep(0.001)
            self.SerialPortB_Flag = self.Uart.SerialPort_Close()
            #打开串口
            self.SerialPortB_Flag = self.Uart.SerialPort_Open(self.SerialPortB_COM, self.SerialPortB_Baud)

            self.Refresh_COM_settings(True)
            
            if self.SerialPortB_Flag == True :
                self.SerialPortB_OnOff.setText("connecting")
                text = '\nconnecting'+str(self.SerialPortB_COM)+', Waitting...\n'
                self.textBroswerPrintRealTime(text)
                
                flag = self.McuInit_show()

                if flag == True:
                    self.SerialPortB_OnOff.setText("关闭/Disconnect")
                    self.SerialPortB.setEnabled(False)   # 串口号变为不可选择
                    text = str(self.SerialPortB_COM)+' Connect Success'+'/'+str(self.SerialPortB_COM)+'连接成功'
                    self.setting.setValue("setup/SerialPortB_ConnectFlag",True)
                    self.label_SerialPort.setStyleSheet('background-color:rgb(0, 255, 0)') 

                else:
                    self.SerialPortB_Flag = self.Uart.SerialPort_Close()
                    text = str(self.SerialPortB_COM)+' ConnectFailed Success'+'/'+str(self.SerialPortB_COM)+'连接失败'
                    text1 = '确认板子 是否已正常上电/连接串口USB'
                    self.textBroswerPrintRealTime(text1)    
                    self.SerialPortB_OnOff.setText("连接/Connect")
                    self.label_SerialPort.setStyleSheet('background-color:rgb(255, 255, 255)') 
            else:
                text = str(self.SerialPortB_COM)+' ConnectFailed Success'+'/'+str(self.SerialPortB_COM)+'连接失败'
                self.SerialPortB_OnOff.setText("连接/Connect")
                self.label_SerialPort.setStyleSheet('background-color:rgb(255, 255, 255)') 
            self.textBroswerPrintRealTime(text,self.print_info_fast)    
            self.textBroswerPrintRealTime(self.Time_text()+'\n') 
        elif self.SerialPortB_OnOff.text() == '关闭/Disconnect' :
            # 先关闭接收线程,然后关闭串口
            self.SerialPortB_Flag = self.Uart.SerialPort_Close()
            
            if self.SerialPortB_Flag == True:
                text = str(self.SerialPortB_COM)+' CloseSuccess'+'/'+str(self.SerialPortB_COM)+'关闭成功'
                self.SerialPortB.setEnabled(True)  # 串口号变为可选择
                self.SerialPortB_OnOff.setText("连接/Connect")
                self.setting.setValue("setup/SerialPortB_ConnectFlag",False)
                self.label_SerialPort.setStyleSheet('background-color:rgb(255, 255, 255)') 
            else:
                text = str(self.SerialPortB_COM)+' CloseFailed'+'/'+str(self.SerialPortB_COM)+'关闭失败'
            self.textBroswerPrintRealTime(text)
            self.textBroswerPrintRealTime(self.Time_text()+'\n')
        else:
            text1 = '请确认连接SerialPortA是否已连接,且板子是否已正常上电'
            self.textBroswerPrintRealTime('\n'+text1)    
            self.textBroswerPrintRealTime(self.Time_text()+'\n')      
    def SerialPort_CheckConnect(self):
        if self.SerialPortB_OnOff.text() == '连接/Connect':
            text = 'PleaseConnect SerialPortB/请先连接串口B '
            QtWidgets.QMessageBox.information(self, "提示", text, QMessageBox.Ok | QMessageBox.Close)
        else: 
            return True

    #使用串口指令框，直接发送数据
    def SerialPortB_DirectSend_PrintTxRxData_cb(self, show_flag):
        # 判断串口是否已经连接
        if self.SerialPort_CheckConnect() == True:
            # 获取 SerialPortB_textEdit框中的内容
            textEdit = self.SerialPortB_textEdit.text().upper()
            if textEdit == '':
                text = 'PleaseInput Commond/内容为空, 请输入指令, '
                self.textBroswerPrintRealTime(text+self.Time_text())
            else:
                for i in range (30):
                    self.Rx_Array[i] = ''                  

                cmd = re.sub(r"\s+", "", textEdit).upper()  # 去除空格
                Action = 'Send Command: '
                if show_flag[1] == True:#False
                    self.textBroswerPrintRealTime(Action)
                    self.textBroswerPrintRealTime(cmd)                         
                
                sleep(0.01) 
                self.Uart.Tx_HexSignal.emit(cmd, self.Action_Num_Normal, show_flag)#触发自定义信号,启动Uart_Tx并判断是否成功发送,1:返回信息进入数据进行保存
                
                self.Uart.start()
                sleep(0.003) 
                #QThread_Run_Flag= True,则等待串口完成数据读取后,并自动关闭串口子线程
                while self.Uart.QThread_Run_Flag == True:
                    if self.setting.value("setup_SerialPortB/Flag_Stop") == False:
                        break                         
                    pass 
                if show_flag[2] == True:
                    self.textBroswerPrintRealTime('')
                self.SerialPortA_RxDataRecord_SeLDone_cb(self.Action_Num_Normal, show_flag, self.Rx_Array)
                
                self.textBroswerPrintRealTime('')      
    #函数 调用串口，进行 写操作，返回：该操作的完成状态
    def SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(self, DaCmd_Raw, Action='', Action_Num = 0, show_flag = [2,True,False]):#传输指令/Rx需读取次数/是否打印TxRX信息的标志位
        # 判断串口是否已经连接
        if self.SerialPort_CheckConnect() == True:
            for i in range (30):#清空数组
                self.Rx_Array[i] = ''             
            
            cmd = re.sub(r"\s+", "", DaCmd_Raw).upper()  # 去除空格
            
            if show_flag[1] == True:#False
                self.textBroswerPrintRealTime(Action)
            if show_flag[2] == True:
                self.textBroswerPrintRealTime(cmd) 
            
            sleep(0.01) 
            self.Uart.Tx_HexSignal.emit(cmd, Action_Num, show_flag)#触发自定义信号,启动Uart_Tx并判断是否成功发送,1:返回信息进入数据进行保存
            
            # self.setting.setValue("setup_SerialPortB/Flag_Stop", True)
            self.Uart.start()
            sleep(0.003)                        
            #QThread_Run_Flag= True,则等待串口完成数据读取后,并自动关闭串口子线程
            while self.Uart.QThread_Run_Flag == True:
                if self.setting.value("setup_SerialPortB/Flag_Stop") == False:
                    break                
                pass 

            if show_flag[2] == True:
                self.textBroswerPrintRealTime('')            
            self.SerialPortA_RxDataRecord_SeLDone_cb(Action_Num, show_flag, self.Rx_Array)
            
            self.CheckDone(self.Rx_Array_buf, Action, show_flag)             
    #函数调用串口，进行 读操作，返回：读取的结果 hex  
    def SerialPortB_SendHexCMD_SelPrint_GetResult_cb(self, DaCmd_Raw, Action='', Action_Num = 0, show_flag = [2,True,False]):#传输指令/Rx需读取次数/是否打印TxRX信息的标志位
        # 判断串口是否已经连接
        if self.SerialPort_CheckConnect() == True:
            for i in range (30):#清空数组
                self.Rx_Array[i] = ''  
            
            cmd = re.sub(r"\s+", "", DaCmd_Raw).upper()  # 去除空格
 
            if show_flag[1] == True:#False
                self.textBroswerPrintRealTime(Action)
            if show_flag[2] == True:
                self.textBroswerPrintRealTime(cmd) 
            
            sleep(0.01) 
            self.Uart.Tx_HexSignal.emit(cmd, Action_Num, show_flag)#触发自定义信号,启动Uart_Tx并判断是否成功发送,1:返回信息进入数据进行保存
            
            # self.setting.setValue("setup_SerialPortB/Flag_Stop", True)    
            self.Uart.start()
            sleep(0.003)                         
            #QThread_Run_Flag= True,则等待串口完成数据读取后,并自动关闭串口子线程
            while self.Uart.QThread_Run_Flag == True:
                if self.setting.value("setup_SerialPortB/Flag_Stop") == False:
                    break      
                pass 
            
            if show_flag[2] == True:
                self.textBroswerPrintRealTime('')
            self.SerialPortA_RxDataRecord_SeLDone_cb(Action_Num, show_flag, self.Rx_Array)
            
            valve_buf = self.GetResult_RxData(self.Rx_Array_buf,show_flag)
            return valve_buf
                           
    #Rx数据完成后， 传递 数据个数/接收完成标志位/ 并自动判断是否打印Rx数据，再根据Action_Num触发 各个处理数据的程序
    def SerialPortA_RxDataRecord_SeLDone_cb(self, Action_Num, show_flag, array):
        self.Action_Num_ID = Action_Num  
        for i in range (show_flag[0]):
                self.Rx_Array_buf[i] = array[i]      
        
        if self.Action_Num_ID < 1000:   #短耗时 指令
            if show_flag[2] == True:
                self.SerialPortB_RxData_Print_cb(show_flag, self.Rx_Array_buf)          
    #打印Rx数据，并确认底层是否接收到正确的Tx信息
    def SerialPortB_RxData_Print_cb(self, show_flag, array):
        if show_flag[2] == True:
            self.textBroswerPrintRealTime('RebackData '+str(show_flag[0])+' Words:')
            for i in range (show_flag[0]):
                    self.textBroswerPrintRealTime(array[i])       
                 
    #处理返回的数据，获取 操作的完成状态
    def CheckDone(self, RxData, action, show_flag):
        try:
            text = str(action).split('/')
            if RxData[show_flag[0]-1][-4:] == 'AFAF':
                text1 = str(text[0]) + " Done/"+ str(text[1])+"执行完成"
            else:
                text1 = str(text[0]) + " Fail/"+ str(text[1])+"执行失败"
        except:
            if RxData[show_flag[0]-1][-4:] == 'AFAF':
                text1 =  "Action Done.  "
            else:
                text1 =  "Action Fail.  "
        if  show_flag[1] == True:       
            self.textBroswerPrintRealTime(text1+self.Time_text()+'\n')       
        if show_flag[2] == True: # 正常单次执行打印打印空格行；多次连续执行=0，则不重复打印空格行
            self.textBroswerPrintRealTime('')
    #处理返回的数据，获取结果
    def GetResult_RxData(self, RxData, show_flag):
        buf = RxData[show_flag[0]-1][-4:]      
        return buf    
    def AdcRead_410_cb(self):#切换为410采样DC光功率
        
        # 判断串口是否已经连接
        if self.SerialPort_CheckConnect() == True:        
            ch = int(self.SerialPortB_ADC.text())
            ch_Hex = hex(ch)[2:].zfill(2)  # DA通道号转换为两位hex格式的字符
            Cmd_Raw = 'AA 82 F1 AA AA'+ch_Hex  # 整理写DA的命令格式

            Action = 'Rd 410_ADC_Ch: '+str(ch_Hex)

            #发送+选择是否打印信息+处理数据获取结果
            value_buf = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(Cmd_Raw, Action, self.Action_Num_Normal, self.print_info_fast)           

            Text = '已读取DC Power_ad_dec: '+ str(int(value_buf,16))
            self.textBroswerPrintRealTime(Text)
            if ch == 7:
                self.textBroswerPrintRealTime('已读取PD ResFlag: '+self.Rx_Array_buf[1][6:8]) 
                volt_AD = int(value_buf,16)/65535*2.5
                volt_PD = int(value_buf,16)/65535*2.5/10*15.1 
                self.textBroswerPrintRealTime('ADC电压: '+str(volt_AD)[0:5]+'V')
                self.textBroswerPrintRealTime('PD电压: '+str(volt_PD)[0:5]+'V')
                self.textBroswerPrintRealTime('')
            elif ch ==4:
                volt_AD = int(value_buf,16)/65535*2.5
                volt_R = int(value_buf,16)/65535*2.5/10*15.1 
                self.textBroswerPrintRealTime('ADC电压: '+str(volt_AD)[0:5]+'V')
                self.textBroswerPrintRealTime('Thermistor电压: '+str(volt_R)[0:5]+'V')
                TEMP2 = volt_R/( (float(self.V_REF)-volt_R)/10 )#电阻值
                try:
                    TEMP3=1/( math.log(TEMP2*1000/10000)/3892+1/(273.15+25) )-273.15
                    self.textBroswerPrintRealTime('CDM_package_temperature: '+str(TEMP3)[0:5]+'℃')
                except:
                    self.textBroswerPrintRealTime('CDM_package_temperature: err report')
                self.textBroswerPrintRealTime('')                
            else:
                volt_AD = int(value_buf,16)/65535*2.5
                volt_PD = int(value_buf,16)/65535*2.5/10*15.1 
                self.textBroswerPrintRealTime('ADC电压: '+str(volt_AD)[0:5]+'V')
                self.textBroswerPrintRealTime('PD电压: '+str(volt_PD)[0:5]+'V')
                self.textBroswerPrintRealTime('')    
    def AdcRead_410_PdADC_cb(self):#切换为410采样DC光功率
        
        # 判断串口是否已经连接
        if self.SerialPort_CheckConnect() == True:        
            Cmd_Raw = 'AA 82 F1 AA AA 08'  # 整理写DA的命令格式

            Action = 'Rd EXPD_Curr:'

            #发送+选择是否打印信息+处理数据获取结果
            value_buf = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(Cmd_Raw, Action, self.Action_Num_Normal, self.print_info_no)           

            Text = '已读取DC Power_ad_dec: '+ str(int(value_buf,16))
            # self.textBroswerPrintRealTime(Text)
    
            self.textBroswerPrintRealTime('已读取PD ResFlag: '+self.Rx_Array_buf[1][6:8]) 
            
            volt_AD = int(value_buf,16)/65535*2.5
            volt_PD = int(value_buf,16)/65535*2.5/10*15.1 
            self.setting_CDM.setValue("LockPoint/PD_Res_flag",self.Rx_Array_buf[1][6:8])
            self.setting_CDM.setValue("LockPoint/LockPoint_EXPD_ADC_Value",str(volt_PD)[0:5]+'V')
        
            # self.textBroswerPrintRealTime('ADC电压: '+str(volt_AD)[0:5]+'V')
            self.textBroswerPrintRealTime('PD电压: '+str(volt_PD)[0:5]+'V')

            
            self.Reback_AdcData.emit( self.Rx_Array_buf[1][6:8],str(volt_PD) )

    def FindPoint_CalPpi_Set_cb(self):
        buf = int( float(self.FindPoint_CalPpi.text())*10 ) 

        buf_hex = hex(buf)[2:].zfill(2)
        
        DA_cmd_Raw = 'AA 03 F1 0B 00 '+buf_hex[-2:] # 整理 写DA的指令格式

        Action = 'Set CalPpi '+str(buf_hex)

        #发送+选择是否打印信息+处理数据获取结果
        self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(DA_cmd_Raw, Action, self.Action_Num_Normal, self.print_info_fast) 
        self.textBroswerPrintRealTime('', self.print_info_fast)     
    def FindPoint_CalPpi_Rd_cb(self):
        
        DA_cmd_Raw = 'AA 83 F1 0B AA AA'# 整理指令格式
        Action = 'Read CalPpi'

        #发送+选择是否打印信息+处理数据获取结果
        Da_Text = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(DA_cmd_Raw, Action, self.Action_Num_Normal, self.print_info_fast) 
        
        buf = str(int(Da_Text,16)/10.0)
        #显示结果
        self.FindPoint_CalPpi.setText(buf)
        
        Text = '已读取 CalPpi: '+buf
        
        #无论是否完成DA操作，都进行信息打印
        self.textBroswerPrintRealTime(Text, self.print_info_fast)
        self.textBroswerPrintRealTime('',  self.print_info_fast)        
             
  #判断heater DA输入格式
    def CheckDa_Form_Range(self, Da_Text, BiasAmpVolt):
        DaForm_OK = ''
        flag = ''
        text = ''
        #优先判断 输入的DA是否都为有效字符
        for char in Da_Text.upper():
            if ord(char) > ord('F') or ord(char) == ord(' ') or ord(char) == '':
                flag = False
                break   
        if flag == False:
            text = 'invalid char/无效字符'
            DaForm_OK = False
        # 再判断 输入字符的个数和格式是否正确
        elif (len(Da_Text) > 4) or (len(Da_Text) < 2): 
            text = "DA Form must be: 0xxx or xxx/DA格式须是0xxx或者xxx"
            DaForm_OK = False
        #判断 是否超出DA上限
        elif int(Da_Text, 16) >= int(BiasAmpVolt, 16):
            text = 'DA out of range/DA超出范围: '+str(BiasAmpVolt.upper())
            DaForm_OK = False
        else:
            DaForm_OK = True
            
        if text != '':    
            QtWidgets.QMessageBox.information(self, "提示", text, QMessageBox.Ok | QMessageBox.Close)    
            
        return DaForm_OK
    #Heater DA写，输入为Hex格式
    def HeaterDa_WriteHex_cb(self, channel, Action_Num = 0, show_flag = [2,True,True]):#增加DA范围限制，不能超过P&D Ref参考电压
        Da_Text = ''
        DA_cmd_Raw = ''
        
        # 判断串口是否已经连接
        if self.SerialPort_CheckConnect() == True:
            #判断下DA的通道号 再进行读取 更有保障

            PushPull_BiasAmpVolt_Hex = hex(int(self.PushPull_BiasAmpVolt/2.0/3.3*4096))
            Da_Text = self.DaShow_channel_list[channel].text().upper() # 获取文本框中的DA值

            #先判断DA的数值是否有效 再进行下发 更有保障
            if self.CheckDa_Form_Range(Da_Text, PushPull_BiasAmpVolt_Hex) == True:
                
                ch = str(channel).zfill(2)
                Da_Text = str(Da_Text).zfill(4)
                DA_cmd_Raw = 'AA 03 F1 '+ str(ch)+' '+Da_Text[0:2]+' '+Da_Text[2:4]# 整理 写DA的指令格式

                Action = 'Set '+str(self.Name_channel_list[channel])+'_DA: '+str(Da_Text)
                
                
                #发送+选择是否打印信息+处理数据获取结果
                self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(DA_cmd_Raw, Action, Action_Num, show_flag) 
                # self.textBroswerPrintRealTime('', show_flag)
                self.DaVolt_Show(channel, self.Dahex_to_HeaterR_Volt(Da_Text), self.PushPull_BiasAmpVolt)
            # else:
            #     text = 'DaForm incorrect/DA格式不正确: '+str(Da_Text)
            #     self.textBroswerPrintRealTime(text)  
            #     self.textBroswerPrintRealTime('')                
    #Heater DA读取，返回Hex格式
    def HeaterDa_ReadHex_cb(self, channel, Action_Num = 0, show_flag = [2,True,True]):
        Text = ''
        Da_Text = ''
        DA_cmd_Raw = ''
        
        # 判断串口是否已经连接
        if self.SerialPort_CheckConnect() == True:
            #判断下DA的通道号 再进行读取 更有保障
            if channel < 8 :
                channel_Hex = hex(channel)[2:].zfill(2)  # DA通道号转换为两位hex格式的字符
                DA_cmd_Raw = 'AA 83 F1 '+channel_Hex+ ' AA AA'  #  整理 读取HeaterDA的指令格式
            else:
                Text = 'HeaterDa channel_Num is wrong/通道序号错误'+ str(channel)
                channel = None
            
            if channel != None:
                Action = 'Read '+str(self.Name_channel_list[channel])+'_DA:'

                #发送+选择是否打印信息+处理数据获取结果
                Da_Text = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(DA_cmd_Raw, Action, Action_Num, show_flag) 
                
                #显示结果
                self.DaShow_channel_list[channel].setText(Da_Text)
                
                Text = '0x '+ str(Da_Text)
                self.DaVolt_Show(channel, self.Dahex_to_HeaterR_Volt(Da_Text), self.PushPull_BiasAmpVolt)
            #无论是否完成DA操作，都进行信息打印
            self.textBroswerPrintRealTime(Text, show_flag)
            
            return Da_Text  #hex值，     可转化为int(Da_Text,16)

    def BiasAmpl_Rd_Wrt(self, RdWrt_flag, Volt_Set = 6.5, Action_Num = 0, show_flag = [2, True, False]):
        
        # 判断串口是否已经连接
        if self.SerialPort_CheckConnect() == True:        
            ch = 10 
            ch_Hex = hex(ch)[2:].zfill(2)  # DA通道号转换为两位hex格式的字符
            PushPull_BiasAmpVolt_buf = ''
            
            if RdWrt_flag == 'Wrt':#写   
                if Volt_Set == 5:
                    value = '0620'#做了少部分电压上的offset补偿
                    DA_cmd_Raw = 'AA 03 F1 '+str(ch_Hex)+' '+str(value)[0:2]+' '+str(value)[2:4] #  整理 读取HeaterDA的指令格式
                elif Volt_Set == 6.5:
                    value = '07F5'#做了少部分电压上的offset补偿
                    DA_cmd_Raw = 'AA 03 F1 '+str(ch_Hex)+' '+str(value)[0:2]+' '+str(value)[2:4] #  整理 读取HeaterDA的指令格式
                    
                Action = 'Set Bais_AmpVolt/设置Bias运放电压: '+ str(Volt_Set)+'V'
                self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(DA_cmd_Raw, Action, Action_Num, show_flag)
                
                self.PushPull_BiasAmpVolt = int(value,16)/4096*3.3*2*2#电路设计上，bias运放的参考源电压由运放*2倍放大而来,bias运放电路又有*2倍放大

                PushPull_BiasAmpVolt_buf = value

            if RdWrt_flag == 'Rd':#读 
                DA_cmd_Raw = 'AA 83 F1 '+str(ch_Hex)+ ' AA AA'  #  整理 读取HeaterDA的指令格式
                Action = 'Rd Bais_AmpVolt... '

                PushPull_BiasAmpVolt_buf = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(DA_cmd_Raw, Action, Action_Num, show_flag)
                self.PushPull_BiasAmpVolt = int(PushPull_BiasAmpVolt_buf,16)/4096*3.3*2*2#电路设计上，bias运放的参考源电压由运放*2倍放大而来,bias运放电路又有*2倍放大
                
                if show_flag[2] == True:
                    self.textBroswerPrintRealTime('', show_flag)
                self.textBroswerPrintRealTime('Bais_AmpVolt/Bias运放电压: '+str(self.PushPull_BiasAmpVolt)[0:5]+'V', show_flag)
            
            if PushPull_BiasAmpVolt_buf == '07EA':#'07F5'
                self.EN_PushPull_Volt_6V5.setChecked(True)
            if PushPull_BiasAmpVolt_buf == '0620':
                self.EN_PushPull_Volt_5V.setChecked(True)  
                
            return self.PushPull_BiasAmpVolt#返回实际电压值 float
                
        else:
            self.EN_PushPull_Volt_6V5.setChecked(False)
            self.EN_PushPull_Volt_5V.setChecked(False)

    def Dahex_to_HeaterR_Volt(self, hex):#输出 Float/V
        try:
            return float(round(int(hex,16)/ 4095.0 * 3.3*2 , 3)*1000/1000) #hex转为10进制数，计算DA电压
        except:
            return 0 #hex转为10进制数，计算DA电压
    def DaVolt_Show(self, ch, Volt, AmpBaisVolt):
        self.VerticalSlider_channel_list[ch].setMinimum(0)
        self.VerticalSlider_channel_list[ch].setMaximum(int(AmpBaisVolt*1000))#int
        self.VerticalSlider_channel_list[ch].setValue(int(Volt*1000))#int
        self.Volt_LCDNumber_channel_list[ch].setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.Volt_LCDNumber_channel_list[ch].setStyleSheet("background-color: white;")
        # self.XI_Volt.setSmallDecimalPoint(True); #小数点不占位置
        self.Volt_LCDNumber_channel_list[ch].setDigitCount(5)
        self.Volt_LCDNumber_channel_list[ch].display(Volt)
   
    def McuInit_show(self):#读取初始化配置 并显示
        try:
            #BiasAmpi电压范围
            self.BiasAmpl_Rd_Wrt('Rd', '', self.Action_Num_Normal, self.print_info_no)
            
            MaxVolt = self.PushPull_BiasAmpVolt#bais运动的实际电压
            
            if MaxVolt > 6:
                self.setting.setValue("setup_BiasVolt_Range/BiasVolt_Range", 6.5)
            else:
                self.setting.setValue("setup_BiasVolt_Range/BiasVolt_Range", 5)
            # print(self.PushPull_BiasAmpVolt)
            
            # #XI XQ YI YQ XP YP 6通道读取NNQ DA值
            for ch in (self.Number_channel_list[1:7]):
                DaValue = self.HeaterDa_ReadHex_cb(self.Number_channel_list[ch], self.Action_Num_Normal, self.print_info_no)
                Da_Volt = self.Dahex_to_HeaterR_Volt(DaValue) #hex转为10进制数，计算DA电压
                self.DaVolt_Show(self.Number_channel_list[ch], Da_Volt, MaxVolt)
                sleep(0.002)
            
            #读取锁定点的模式，0=MinMinQuad, 1 = MaxMaxMax
            self.BiasPoint_Mode = self.Get_BiasPiont_Mode()
            self.set_BiasPiont_Mode_cb(self.BiasPoint_Mode)
            return True
        except:
            return False
    def Refresh_6ch_HeaterDA(self):
        MaxVolt = self.PushPull_BiasAmpVolt
        #XI XQ YI YQ XP YP 6通道读取NNQ DA值
        for ch in (self.Number_channel_list[1:7]):
            DaValue = self.HeaterDa_ReadHex_cb(self.Number_channel_list[ch], self.Action_Num_Normal, self.print_info_no)
            Da_Volt = self.Dahex_to_HeaterR_Volt(DaValue) #hex转为10进制数，计算DA电压
            self.DaVolt_Show(self.Number_channel_list[ch], Da_Volt, MaxVolt)      
        
    def NNQ_Record_Save_cb(self):#从文本框处读取NNQ保存，增加从偏置板读取极性然后保存
        
        self.update_WL_Temperature()
        BiasPiont_buf = ''
        self.CDM_SN_buf = self.setting_CDM.value("setup/CDM_SN")
        self.TEC_temperature = self.setting_CDM.value("setup/T0")
        self.ITLA_WL = round(float(self.setting_CDM.value("setup/WL0")),1)  
        
        self.textBroswerPrintRealTime('\nCDM_SN: '+str(self.CDM_SN_buf))     
        self.textBroswerPrintRealTime('TEC_temperature: '+str(self.TEC_temperature)+' , ITLA_WL: '+str(self.ITLA_WL))
        
        #默认从偏置控制板读取NNQ 进行保存；  也可选择从GUI保存NNQ
        if self.LockPoint_NNQ_SaveFromFW.isChecked() == True:
            
            if self.Lock_MaxMaxMax_EN.isChecked() == True:
                BiasPiont_buf = '_MaxMaxMax'
            elif self.Lock_MinMinQuad_EN.isChecked() == True:
                BiasPiont_buf = '_MinMinQuad'
                
            #XI XQ YI YQ XP YP 6通道读取NNQ DA值
            for ch in (self.Number_channel_list[1:7]):
                ch_Hex = hex(ch)[2:].zfill(2)  # DA通道号转换为两位hex格式的字符
                cmd_text_Raw = 'AA 83 F1 '+ch_Hex+ ' AA AA'  # 整理写DA的命令格式
                Action = 'Get LockPoint '+str(self.Name_channel_list[ch])+ ' DA'
                Da_Buf = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text_Raw, Action, self.Action_Num_Normal, self.print_info_no)
                self.setting_CDM.setValue('LockPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                          +"/LockPoint_"+str(self.Name_channel_list[ch]), str(Da_Buf))
                
            #XPhase极性,只有在找点时确认极性
            cmd_text_Raw = 'AA 84 F1 B5 FA AA'    # 读取DA的命令格式
            Action =  'Get LockPoint XP 极性'
            Da_Buf = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text_Raw, Action, self.Action_Num_Normal, self.print_info_no)
            if str(Da_Buf)[-2:] == '00':
                self.setting_CDM.setValue("LockPoint_"+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                          +"/FindPoint_XP_QuadFlag", 'DOWN')
            elif str(Da_Buf)[-2:] == '01':
                self.setting_CDM.setValue('LockPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                          +"/FindPoint_XP_QuadFlag", 'UP')

            #YPhase极性,只有在找点时确认极性
            cmd_text_Raw = 'AA 84 F1 B6 FA AA'    # 读取DA的命令格式
            Action =  'Get LockPoint YP 极性'
            Da_Buf = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text_Raw, Action, self.Action_Num_Normal, self.print_info_no)
            if str(Da_Buf)[-2:] == '00':
                self.setting_CDM.setValue('LockPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                          +"/FindPoint_YP_QuadFlag", 'DOWN')
            elif str(Da_Buf)[-2:] == '01':
                self.setting_CDM.setValue('LockPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                          +"/FindPoint_YP_QuadFlag", 'UP')


            #默认从偏置控制板读取NNQ 进行保存；  也可选择从GUI保存
            #XI XQ YI YQ XP YP 6通道读取NNQ DA值
            for ch in (self.Number_channel_list[1:7]):
                ch_Hex = hex(ch)[2:].zfill(2)  # DA通道号转换为两位hex格式的字符
                cmd_text_Raw = 'AA 83 F2 '+ch_Hex+ ' AA AA'  # 整理写DA的命令格式
                Action = 'Get FindPoint '+str(self.Name_channel_list[ch])+ ' DA'
                Da_Buf = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text_Raw, Action, self.Action_Num_Normal, self.print_info_no)
                self.setting_CDM.setValue('FindPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                          +"/FindPoint_"+str(self.Name_channel_list[ch]), str(Da_Buf))

            #XPhase极性,只有在找点时确认极性
            cmd_text_Raw = 'AA 84 F1 B5 FA AA'    # 读取DA的命令格式
            Action =  'Get FindPoint XP 极性'
            Da_Buf = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text_Raw, Action, self.Action_Num_Normal, self.print_info_no)
            if str(Da_Buf)[-2:] == '00':
                self.setting_CDM.setValue('FindPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                          +"/FindPoint_XP_QuadFlag", 'DOWN')
            elif str(Da_Buf)[-2:] == '01':
                self.setting_CDM.setValue('FindPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                          +"/FindPoint_XP_QuadFlag", 'UP')

            #YPhase极性,只有在找点时确认极性
            cmd_text_Raw = 'AA 84 F1 B6 FA AA'    # 读取DA的命令格式
            Action =  'Get FindPoint YP 极性'
            Da_Buf = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text_Raw, Action, self.Action_Num_Normal, self.print_info_no)
            if str(Da_Buf)[-2:] == '00':
                self.setting_CDM.setValue('FindPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                          +"/FindPoint_YP_QuadFlag", 'DOWN')
            elif str(Da_Buf)[-2:] == '01':
                self.setting_CDM.setValue('FindPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                          +"/FindPoint_YP_QuadFlag", 'UP')
                     
            self.textBroswerPrintRealTime('From FW Get NNQRecord and Save To ConfigFile Done.')
            
        elif self.LockPoint_NNQ_SaveFromGUI.isChecked() == True:
            
            #读取 GUI的NNQ数值进行保存，增加了可修改LockdPoint NNQ的便利性
            self.textBroswerPrintRealTime('GUI LockPoint_NNQRecord_SaveTo ConfigFile... ')  
            
            #XI XQ YI YQ XP YP 6通道
            for ch in (self.Number_channel_list[1:7]):
                Da_Buf = self.LockPoint_NNQ_channel_list[ch].text()# LockPoint_NNQ 
                self.setting_CDM.setValue("LockPoint/LockPoint_"+str(self.Name_channel_list[ch]), str(Da_Buf))
                self.textBroswerPrintRealTime(str(self.Name_channel_list[ch])+': '+str(Da_Buf))

            XPhase_QuadFlag = self.XPhase_QuadFlag.text()# XPhase_QuadFlag
            if XPhase_QuadFlag.upper() =='UP' or XPhase_QuadFlag.upper() == 'DOWN':
                self.setting_CDM.setValue("FindPoint/FindPoint_XP_QuadFlag", XPhase_QuadFlag.upper())
                
                self.setting_CDM.setValue('LockPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                                 +"/FindPoint_XP_QuadFlag", XPhase_QuadFlag.upper())
            else:
                self.XPhase_QuadFlag.setText('') 
                text = 'XPhase极性只能填写UP或者DOWN其中之一' 
                QtWidgets.QMessageBox.information(self, "提示", text, QMessageBox.Ok | QMessageBox.Close) 
                
            
            YPhase_QuadFlag = self.YPhase_QuadFlag.text()# YPhase_QuadFlag
            if YPhase_QuadFlag.upper() =='UP' or YPhase_QuadFlag.upper() == 'DOWN':
                self.setting_CDM.setValue("FindPoint/FindPoint_YP_QuadFlag", YPhase_QuadFlag.upper())
                self.setting_CDM.setValue('LockPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                                 +"/FindPoint_YP_QuadFlag", YPhase_QuadFlag.upper())                
                
            else:
                self.YPhase_QuadFlag.setText('')
                text = 'YPhase极性只能填写UP或者DOWN其中之一' 
                QtWidgets.QMessageBox.information(self, "提示", text, QMessageBox.Ok | QMessageBox.Close)
                  
            self.textBroswerPrintRealTime('GUI LockPoint_NNQRecord_SaveTo ConfigFile Done.')  
        self.textBroswerPrintRealTime(self.Time_text()+'\n')                                                                        
    
    def LockPoint_NNQRecord_Read_cb(self):#从配置文件读取NNQ记录
        BiasPiont_buf = ''
        if self.Lock_MaxMaxMax_EN.isChecked() == True:
            BiasPiont_buf = '_MaxMaxMax'
        elif self.Lock_MinMinQuad_EN.isChecked() == True:
            BiasPiont_buf = '_MinMinQuad'
        
        
        self.CDM_SN_buf = self.setting_CDM.value("setup/CDM_SN")
        self.TEC_temperature = self.setting_CDM.value("setup/T0")
        self.ITLA_WL = round(float(self.setting_CDM.value("setup/WL0")),1)     
        self.textBroswerPrintRealTime('TEC_temperature: '+str(self.TEC_temperature)+' , ITLA_WL: '+str(self.ITLA_WL))        
        self.textBroswerPrintRealTime('Read LockPoint_NNQ From ConfigFile...')
        
        #XI XQ YI YQ XP YP 6通道读取NNQ DA值
        for ch in (self.Number_channel_list[1:7]):
            Da_Buf = self.setting_CDM.value('LockPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                            +"/LockPoint_"+str(self.Name_channel_list[ch]))
            self.LockPoint_NNQ_channel_list[ch].setText(Da_Buf)# LockPoint_NNQ
            self.textBroswerPrintRealTime(str(self.Name_channel_list[ch])+': '+str(Da_Buf))

        XPhase_QuadFlag = self.setting_CDM.value('LockPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                                 +"/FindPoint_XP_QuadFlag")
        self.XPhase_QuadFlag.setText(XPhase_QuadFlag)# FindPoint XP DA
        self.textBroswerPrintRealTime('XP极性: '+str(XPhase_QuadFlag))
        
        YPhase_QuadFlag = self.setting_CDM.value('LockPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                                 +"/FindPoint_YP_QuadFlag")
        self.YPhase_QuadFlag.setText(YPhase_QuadFlag)# FindPoint YP DA
        self.textBroswerPrintRealTime('YP极性: '+str(YPhase_QuadFlag))

        
        self.textBroswerPrintRealTime('Read LockPoint_NNQ From ConfigFile Done.')
        self.textBroswerPrintRealTime(self.Time_text()+'\n') 
    def LockPoint_NNQRecord_Set_cb(self):#从配置文件读取NNQ和Phase极性，然后下发设置
        if self.Lock_MaxMaxMax_EN.isChecked() == True:
            BiasPiont_buf = '_MaxMaxMax'
        elif self.Lock_MinMinQuad_EN.isChecked() == True:
            BiasPiont_buf = '_MinMinQuad'        

        self.textBroswerPrintRealTime('Set LockPoint_NNQ_DA From ConfigFile...')
        self.CDM_SN_buf = self.setting_CDM.value("setup/CDM_SN")
        self.TEC_temperature = self.setting_CDM.value("setup/T0")
        self.ITLA_WL = round(float(self.setting_CDM.value("setup/WL0")),1)          
        
        self.textBroswerPrintRealTime('TEC_temperature: '+str(self.TEC_temperature)+' , ITLA_WL: '+str(self.ITLA_WL))
        # 判断串口是否已经连接
        if self.SerialPort_CheckConnect() == True:
            if self.LockPoint_NNQ_channel_list[1].text() != '':
                
                
                    #XI XQ YI YQ XP YP 6通道读取NNQ DA值
                    for ch in (self.Number_channel_list[1:7]):
                        
                        ch_Hex = str(ch).zfill(2)
                        Da_Buf = self.LockPoint_NNQ_channel_list[ch].text().zfill(4)# LockPoint_NNQ DA
                        cmd_Raw = 'AA 03 F1 '+ ch_Hex + Da_Buf[-4:-2] + Da_Buf[-2:]   # 整理写DA的命令格式
                        
                        show_flag = self.print_info_no
                        Action = 'Set '+self.Name_channel_list[ch]+'_DA'
                        if show_flag[2] == False:
                            self.textBroswerPrintRealTime(Action) 
                        self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_Raw, Action, self.Action_Num_Normal, show_flag)
                        
                            
                    #Phase极性
                    flag = self.setting_CDM.value('LockPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                                 +"/FindPoint_XP_QuadFlag")# FindPoint_XP_QuadFlag
                    if flag == 'DOWN':
                        cmd_Raw = 'AA 04 F1 B5 FA 00' # 整理写DA的命令格式
                    elif flag == 'UP':
                        cmd_Raw = 'AA 04 F1 B5 FA 01' # 整理写DA的命令格式     
                        
                    show_flag = self.print_info_no
                    Action = 'Set XP_QuadFlag: '+ flag
                    if show_flag[2] == False:
                        self.textBroswerPrintRealTime(Action)       
                    self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_Raw, Action, self.Action_Num_Normal, show_flag)

                    flag = self.setting_CDM.value('LockPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                                 +"/FindPoint_YP_QuadFlag")# FindPoint_XP_QuadFlag
                    if flag == 'DOWN':
                        cmd_Raw = 'AA 04 F1 B6 FA 00' # 整理写DA的命令格式
                    elif flag == 'UP':
                        cmd_Raw = 'AA 04 F1 B6 FA 01' # 整理写DA的命令格式     

                    show_flag = self.print_info_no
                    Action = 'Set YP_QuadFlag: '+ flag
                    if show_flag[2] == False:
                        self.textBroswerPrintRealTime(Action)            
                    self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_Raw, Action, self.Action_Num_Normal, show_flag)


                    self.Refresh_6ch_HeaterDA()
                    self.textBroswerPrintRealTime('Set LockPoint_NNQ_DA From ConfigFile Done.')
            else:
                    self.textBroswerPrintRealTime('Set LockPoint_NNQ_DA From ConfigFile Fail.')
                    self.textBroswerPrintRealTime('先读取NNQ记录,再进行NNQ设置.')
        self.textBroswerPrintRealTime('Please connect COM')
        self.textBroswerPrintRealTime(self.Time_text()+'\n')           

    def FindPoint_NNQRecord_Read_cb(self):#直接从配置文件读取NNQ记录
        if self.Lock_MaxMaxMax_EN.isChecked() == True:
            BiasPiont_buf = '_MaxMaxMax'
        elif self.Lock_MinMinQuad_EN.isChecked() == True:
            BiasPiont_buf = '_MinMinQuad'        
        
        self.CDM_SN_buf = self.setting_CDM.value("setup/CDM_SN")
        self.TEC_temperature = self.setting_CDM.value("setup/T0")
        self.ITLA_WL = round(float(self.setting_CDM.value("setup/WL0")),1)     
        self.textBroswerPrintRealTime('TEC_temperature: '+str(self.TEC_temperature)+' , ITLA_WL: '+str(self.ITLA_WL))        
        self.textBroswerPrintRealTime('Read FindPoint_NNQ From ConfigFile...')
        
        #XI XQ YI YQ XP YP 6通道读取NNQ DA值
        for ch in (self.Number_channel_list[1:7]):
            Da_Buf = self.setting_CDM.value('FindPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                            +'/'+"FindPoint_"+str(self.Name_channel_list[ch]))
            self.FindPoint_NNQ_channel_list[ch].setText(Da_Buf)# LockPoint_NNQ
            self.textBroswerPrintRealTime(str(self.Name_channel_list[ch])+': '+str(Da_Buf))


        XPhase_QuadFlag = self.setting_CDM.value('FindPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                                 +'/'+"FindPoint_XP_QuadFlag")
        self.XPhase_QuadFlag.setText(XPhase_QuadFlag)# FindPoint XP DA
        self.textBroswerPrintRealTime('XP极性: '+str(XPhase_QuadFlag))
        
        YPhase_QuadFlag = self.setting_CDM.value('FindPoint_'+str(self.CDM_SN_buf)+"_"+str(self.ITLA_WL)+"_"+str(self.TEC_temperature)+"C"+BiasPiont_buf
                                                 +'/'+"FindPoint_YP_QuadFlag")
        self.YPhase_QuadFlag.setText(YPhase_QuadFlag)# FindPoint YP DA
        self.textBroswerPrintRealTime('YP极性: '+str(YPhase_QuadFlag))

        
        self.textBroswerPrintRealTime('Read FindPoint_NNQ From ConfigFile Done.')
        self.textBroswerPrintRealTime(self.Time_text()+'\n') 
    def FindPoint_Record_Set_cb(self):#考虑增加极性配置
        # print('\nSet FindPoint_Record...')
        self.textBroswerPrintRealTime('\nSet FindPoint_Record...')

        # 下发FindPoint DA值,直接使用写DA命令
        Da_Buf = self.FindPoint_XI.text()# FindPoint XI DA
        # Da_Buf_Hex1 = str(Da_Buf)[0:1].zfill(2)  # 转换为两位hex格式的字符
        cmd_text = 'AA 03 F1 01 '+ Da_Buf[-4:-2].zfill(2) + Da_Buf[-2:]   # 整理写DA的命令格式
        cmd_text_Raw = re.sub(r"\s+", "", cmd_text)#去除空格
        # print(cmd_text_Raw)
        Da_Buf = self.DaData_Write_hex(cmd_text_Raw, cmd_text)

    
        Da_Buf = self.FindPoint_XQ.text()# FindPoint XQ DA
        cmd_text = 'AA 03 F1 02 '+ Da_Buf[-4:-2].zfill(2) + Da_Buf[-2:]   # 整理写DA的命令格式
        cmd_text_Raw = re.sub(r"\s+", "", cmd_text)#去除空格
        # print(cmd_text_Raw)
        Da_Buf = self.DaData_Write_hex(cmd_text_Raw, cmd_text)

        Da_Buf = self.FindPoint_XP.text()# FindPoint XP DA
        cmd_text = 'AA 03 F1 05 '+ Da_Buf[-4:-2].zfill(2) + Da_Buf[-2:]   # 整理写DA的命令格式
        cmd_text_Raw = re.sub(r"\s+", "", cmd_text)#去除空格
        # print(cmd_text_Raw)
        Da_Buf = self.DaData_Write_hex(cmd_text_Raw, cmd_text)

        Da_Buf = self.FindPoint_YI.text()# FindPoint YI DA
        cmd_text = 'AA 03 F1 03 '+ Da_Buf[-4:-2].zfill(2) + Da_Buf[-2:]   # 整理写DA的命令格式
        cmd_text_Raw = re.sub(r"\s+", "", cmd_text)#去除空格
        # print(cmd_text_Raw)
        Da_Buf = self.DaData_Write_hex(cmd_text_Raw, cmd_text)

        Da_Buf = self.FindPoint_YQ.text()# FindPoint YQ DA
        cmd_text = 'AA 03 F1 04 '+ Da_Buf[-4:-2].zfill(2) + Da_Buf[-2:]   # 整理写DA的命令格式
        cmd_text_Raw = re.sub(r"\s+", "", cmd_text)#去除空格
        # print(cmd_text_Raw)
        Da_Buf = self.DaData_Write_hex(cmd_text_Raw, cmd_text)

        Da_Buf = self.FindPoint_YP.text()# FindPoint YP DA
        cmd_text = 'AA 03 F1 06 '+ Da_Buf[-4:-2].zfill(2) + Da_Buf[-2:]   # 整理写DA的命令格式
        cmd_text_Raw = re.sub(r"\s+", "", cmd_text)#去除空格
        # print(cmd_text_Raw)
        Da_Buf = self.DaData_Write_hex(cmd_text_Raw, cmd_text)    

        # Da_Buf = self.setting.value("setup/FindPoint_XP_QuadFlag")# FindPoint_XP_QuadFlag
        # cmd_text = 'AA 04 F1 5C '+ Da_Buf[-4:-2].zfill(2) + Da_Buf[-2:]   # 整理写DA的命令格式
        # cmd_text_Raw = re.sub(r"\s+", "", cmd_text)#去除空格
        # print(cmd_text_Raw)
        # Da_Buf = self.DaData_Write_hex(cmd_text_Raw, cmd_text)

        # Da_Buf = self.setting.value("setup/FindPoint_YP_QuadFlag")# FindPoint_XP_QuadFlag
        # cmd_text = 'AA 04 F1 6C '+ Da_Buf[-4:-2].zfill(2) + Da_Buf[-2:]   # 整理写DA的命令格式
        # cmd_text_Raw = re.sub(r"\s+", "", cmd_text)#去除空格
        # print(cmd_text_Raw)
        # Da_Buf = self.DaData_Write_hex(cmd_text_Raw, cmd_text)    

    def EXPD_AligPoint_Rd_cb(self, show_flag):

        cmd_text = 'AA 84 F1 A4 FA AA'
        Action = 'Read AligPoint_EXPD'
        Point = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, show_flag)
        buf = str(int(Point,16))[-1:]
        self.EXPD_AligPoint.setText(buf)#mV
        self.textBroswerPrintRealTime('Read AligPoint_EXPD: '+ buf, show_flag) 
        self.textBroswerPrintRealTime('', show_flag)
    def EXPD_AligPoint_Set_cb(self, show_flag):
        Point = self.EXPD_AligPoint.text()
        if Point == '':
            self.textBroswerPrintRealTime('AligPoint_EXPD can`t be empty')
        elif 0 > int(Point) and int(Point) > 12:
            self.textBroswerPrintRealTime('AligPoint_EXPD must 0< Point < 12')

        else:
            hex_buf = '0x'+f"{int(Point):04X}"#转化为带0x的4位16进制数
            cmd_text = 'AA 04 F1 A4 FA '+ str(hex_buf)[-2:]
            Action = 'Set EXPD_AligPoint: '+ str(Point)
            self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, Action, self.Action_Num_Normal, show_flag)
        self.textBroswerPrintRealTime('')
    def EXPD_IQLockPoint_RefVolt_Rd_cb(self, show_flag):
        
        cmd_text = 'AA 84 F1 A1 AA AA'
        Action = 'Read EXPD_IQLockPoint_RefVolt'
        RefVolt = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, show_flag)
        buf = str(int(RefVolt,16)/10000.0)[:7]
        self.EXPD_IQLockPoint_RefVolt.setText(buf)#mV
        self.textBroswerPrintRealTime('Read EXPD_IQLockPoint_RefVolt: '+ buf +'V', show_flag)  
        self.textBroswerPrintRealTime('', show_flag) 
    def EXPD_IQLockPoint_RefVolt_Set_cb(self, show_flag, flag = 0, Amp = 0):
        if flag == 0:
            RefVolt = self.EXPD_IQLockPoint_RefVolt.text()
        else:
            RefVolt = str(Amp)
        
        if RefVolt != '':
            if 0 < float(RefVolt) and float(RefVolt) <2:
                hex_buf = '0x'+f"{int( float(RefVolt)*10000 ):04X}"#转化为带0x的4位16进制数
                
                cmd_text = 'AA 04 F1 A1 '+ str(hex_buf)[-4:-2]+' '+ str(hex_buf)[-2:]
                Action = 'Set EXPD_IQLockPoint_RefVolt: '+ str(RefVolt) + 'V'
                self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, Action, self.Action_Num_Normal, show_flag)
            else:
                self.textBroswerPrintRealTime('EXPD_IQLockPoint_RefVolt must 1< Point < 2V')
        else:
            self.textBroswerPrintRealTime('RefVolt Can be entry')    
    def EXPD_IQLockThreshold_Rd_cb(self, show_flag):
                # 判断串口是否已经连接
        if self.SerialPort_CheckConnect() == True:    
            cmd_text = 'AA 84 F1 A4 AA AA'
            Value_buf = '' 
            text = '' 
            Action = 'Rd EXPD_IQLockThreshold/读取IQ锁定门限'       
            Value = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, show_flag)
            Value_buf = str(float(round( int(Value, 16)/100.0, 5)))[:4]
            
            self.EXPD_IQLockThreshold.setText(Value_buf)
            self.textBroswerPrintRealTime('Read EXPD_IQLockThreshold: '+Value_buf+'mV\n', show_flag) 
    def EXPD_IQLockThreshold_Set_cb(self, show_flag, flag = 0, Amp = 0):
        if flag == 0:
            LockingThreshold = self.EXPD_IQLockThreshold.text()
        else:
            LockingThreshold = str(Amp)

        if float(LockingThreshold) > 0.01 and float(LockingThreshold) < 30:
            
            hex_buf = '0x'+f"{int(  float(LockingThreshold)/1000*100000  ):04X}"#转化为带0x的4位16进制数
            
            cmd_text = 'AA 04 F1 A4 '+ str(hex_buf)[-4:-2]+' '+ str(hex_buf)[-2:]
            Action = 'Set EXPD_IQLockThreshold_Set: '+ LockingThreshold +'mV'
            self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, Action, self.Action_Num_Normal, show_flag)
        else:
            self.textBroswerPrintRealTime('EXPD_IQLockThreshold_Set must be: 0.01 < Threshold < 30mV')
            self.textBroswerPrintRealTime('Set EXPD_IQLockThreshold_Set Fail'+self.Time_text())

    #扫描调制曲线：写Heater DA，输入为Hex格式
    def ModulationCurve_HeaterDa_WriteHex_cb(self, channel, DA_hex, Action_Num = 0, show_flag = [2,True,True]):#增加DA范围限制，不能超过P&D Ref参考电压
        Da_Text = ''
        DA_cmd_Raw = ''
        
        # 判断串口是否已经连接
        if self.SerialPort_CheckConnect() == True:

            ch = str(channel).zfill(2)
            Da_Text = str(DA_hex)[-4:]
            
            #显示DA_hex
            self.DaShow_channel_list[channel].setText(Da_Text)
                
            DA_cmd_Raw = 'AA 03 F1 '+ str(ch)+' '+Da_Text[0:2]+' '+Da_Text[2:4]# 整理 写DA的指令格式

            Action = 'Set '+str(self.Name_channel_list[channel])+'_DA: '+str(Da_Text)
            
            #发送+选择是否打印信息+处理数据获取结果
            self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(DA_cmd_Raw, Action, Action_Num, show_flag) 
            self.DaVolt_Show(channel, self.Dahex_to_HeaterR_Volt(Da_Text), self.PushPull_BiasAmpVolt)

    def Get_BiasPiont_Mode(self):
        flag = ''
     
        # 判断串口是否已经连接
        if self.SerialPort_CheckConnect() == True:        
            try:
                cmd = 'AA 8A F1 02 AA AA' 
                Action = 'Get BiasPiont_Mode:'
                flag = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd, Action, self.Action_Num_Normal, self.print_info_fast)
                
                #0=MinMinQuad; 1=MaxMaxMax
                if int(flag[-2:]) == 1:
                    self.BiasPoint_Mode = 1
                    self.Lock_MaxMaxMax_EN.setChecked(True)
                    self.Lock_MinMinQuad_EN.setChecked(False)
                    self.textBroswerPrintRealTime('BiasPiont_Mode@MaxMaxMax Enable\n')
                    # cmd_Raw = 'AA 0A 00 02 00 01'
                    # Action = 'LockingPoint@MaxMaxMax Enable'

                    # #发送+选择是否打印信息+处理数据获取结果
                    # self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_Raw, Action, self.Action_Num_Normal, self.print_info_fast) 
                elif int(flag[-2:]) == 0:
                    self.BiasPoint_Mode = 0
                    self.Lock_MaxMaxMax_EN.setChecked(False)
                    self.Lock_MinMinQuad_EN.setChecked(True)
                    self.textBroswerPrintRealTime('BiasPiont_Mode@MinMinQuad Enable\n')
                    # cmd_Raw = 'AA 0A 00 02 00 00'
                    # Action = 'LockingPoint@MinMinQuad Enable'
                    # #发送+选择是否打印信息+处理数据获取结果
                    # self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_Raw, Action, self.Action_Num_Normal, self.print_info_fast) 
                # else:
                #     self.textBroswerPrintRealTime('Please Set BiasPiont_Mode\n')  
                return self.BiasPoint_Mode
            except:
                self.textBroswerPrintRealTime('Get BiasPiont_Mode Fail\n')  
  
        else:
            self.textBroswerPrintRealTime('Please Check the COM Connect')  
    def set_BiasPiont_Mode_cb(self, flag):

        if flag == 1:
            self.Lock_MaxMaxMax_EN.setChecked(True)
            self.Lock_MinMinQuad_EN.setChecked(False)
            self.BiasPoint_Mode = 1
            cmd_Raw = 'AA 0A 00 02 00 01'
            Action = 'Set Lock@MaxMaxMax Enable'

            #发送+选择是否打印信息+处理数据获取结果
            self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_Raw, Action, self.Action_Num_Normal, self.print_info_fast) 
        elif flag == 0:
            self.BiasPoint_Mode = 0
            self.Lock_MaxMaxMax_EN.setChecked(False)
            self.Lock_MinMinQuad_EN.setChecked(True)
            cmd_Raw = 'AA 0A 00 02 00 00'
            Action = 'Set Lock@MinMinQuad Enable'

            #发送+选择是否打印信息+处理数据获取结果
            self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_Raw, Action, self.Action_Num_Normal, self.print_info_fast) 
        else:
            self.textBroswerPrintRealTime('Please Set BiasPiont_Mode\n')  
    def BiasControl_SelectMode_cb(self, flag):
        text = ''
        DA_cmd_Raw = ''
        if flag == 'PushPull':    
            DA_cmd_Raw = 'AA 0A 00 03 00 00'
            text = 'PushPull'
            self.BiasControl_PushPull_En.setChecked(True)
            self.BiasControl_P_arm_En.setChecked(False)
            self.BiasControl_N_arm_En.setChecked(False)
        elif flag == 'P_arm':
            DA_cmd_Raw = 'AA 0A 00 04 00 00'
            text = 'P_arm'     
            self.BiasControl_PushPull_En.setChecked(False)
            self.BiasControl_P_arm_En.setChecked(True)
            self.BiasControl_N_arm_En.setChecked(False)             
        elif flag == 'N_arm':
            DA_cmd_Raw = 'AA 0A 00 05 00 00'
            text = 'N_arm'        
            self.BiasControl_PushPull_En.setChecked(False)
            self.BiasControl_P_arm_En.setChecked(False)
            self.BiasControl_N_arm_En.setChecked(True)

        Action = 'Set BiasControl@'+ text +' Enable'
        #发送+选择是否打印信息+处理数据获取结果
        self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(DA_cmd_Raw, Action, self.Action_Num_Normal, self.print_info_fast) 
        self.textBroswerPrintRealTime('', self.print_info_fast)  


    def Time_text(self):
        return datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    
    #读取 dither  
    def XI_LockDither_Rd_cb(self, print_info = [2, True, False]): 
        cmd_text = 'AA 84 F2 01 AA AA'
        Action = 'Read XI_LockDither'

        DitherAmp = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, print_info)
        buf = str(int(DitherAmp,16))[:4]
        self.XI_LockDither.setText(buf)#mV
        self.textBroswerPrintRealTime(self.Name_channel_list[1]+'_LockDither: '+ buf +'mV\n', print_info)     
    def XQ_LockDither_Rd_cb(self, print_info = [2, True, False]):
        cmd_text = 'AA 84 F2 02 AA AA'
        Action = 'Read XQ_LockDither'
        DitherAmp = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, print_info)
        buf = str(int(DitherAmp,16))[:4]
        self.XQ_LockDither.setText(buf)#mV
        self.textBroswerPrintRealTime(self.Name_channel_list[2]+'_LockDither: '+ buf +'mV\n', print_info)
    def YI_LockDither_Rd_cb(self, print_info = [2, True, False]):
        cmd_text = 'AA 84 F2 03 AA AA'
        Action = 'Read YI_LockDither'
        DitherAmp = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, print_info)
        buf = str(int(DitherAmp,16))[:4]
        self.YI_LockDither.setText(buf)#mV
        self.textBroswerPrintRealTime(self.Name_channel_list[3]+'_LockDither: '+ buf +'mV\n', print_info)      
    def YQ_LockDither_Rd_cb(self, print_info = [2, True, False]):
        cmd_text = 'AA 84 F2 04 AA AA'
        Action = 'Read YQ_LockDither'
        DitherAmp = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, print_info)
        buf = str(int(DitherAmp,16))[:4]
        self.YQ_LockDither.setText(buf)#mV
        self.textBroswerPrintRealTime(self.Name_channel_list[4]+'_LockDither: '+ buf +'mV\n', print_info)       
    def XP_LockDither_Rd_cb(self, print_info = [2, True, False]):
        cmd_text = 'AA 84 F2 05 AA AA'
        Action = 'Read XPhaseDither_I'
        DitherAmp = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, print_info)
        buf = str(int(DitherAmp,16))[:4]
        self.XPhaseDither_I.setText(buf)#mV
        self.textBroswerPrintRealTime(self.Name_channel_list[5]+'_LockDither_I: '+ buf +'mV', print_info)   
            
        cmd_text = 'AA 84 F2 05 AB AA'
        Action = 'Read XPhaseDither_Q'
        DitherAmp = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, print_info)
        buf = str(int(DitherAmp,16))[:4]
        self.XPhaseDither_Q.setText(buf)#mV
        self.textBroswerPrintRealTime(self.Name_channel_list[5]+'_LockDither_Q: '+ buf +'mV\n', print_info)                 
    def YP_LockDither_Rd_cb(self, print_info = [2, True, False]):
        cmd_text = 'AA 84 F2 06 AA AA'
        Action = 'Read YPhaseDither_I'
        DitherAmp = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, print_info)
        buf = str(int(DitherAmp,16))[:4]
        self.YPhaseDither_I.setText(buf)#mV
        self.textBroswerPrintRealTime(self.Name_channel_list[6]+'_LockDither_I: '+ buf +'mV', print_info)   
            
        cmd_text = 'AA 84 F2 06 AB AA'
        Action = 'Read YPhaseDither_Q'
        DitherAmp = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, print_info)
        buf = str(int(DitherAmp,16))[:4]
        self.YPhaseDither_Q.setText(buf)#mV
        self.textBroswerPrintRealTime(self.Name_channel_list[6]+'_LockDither_Q: '+ buf +'mV\n', print_info)                 
    #设置 dither 
    def XI_LockDither_Set_cb(self, flag, Amp, print_info = [2, True, False]):
        if flag == 0:
            DitherAmp = self.XI_LockDither.text()
        else:
            DitherAmp = str(Amp)
        if float(DitherAmp) < 100:
            hex_buf = '0x'+f"{int(float(DitherAmp)):04X}"#转化为带0x的4位16进制数
            
            cmd_text = 'AA 04 F2 01 AA '+ str(hex_buf)[-2:]
            action = 'Set XI_LockDither: '+ DitherAmp +'mV'
            self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, action, self.Action_Num_Normal, print_info)
        else:
            self.textBroswerPrintRealTime('XI_LockDither must < 100mV')
    def XQ_LockDither_Set_cb(self, flag, Amp, print_info = [2, True, False]):
        if flag == 0:
            DitherAmp = self.XQ_LockDither.text()
        else:
            DitherAmp = str(Amp)
        
        if int(DitherAmp) < 100:
            hex_buf = '0x'+f"{int(float(DitherAmp)):04X}"#转化为带0x的4位16进制数
            
            cmd_text = 'AA 04 F2 02 AA '+ str(hex_buf)[-2:]
            action = 'Set XQ_LockDither: '+ DitherAmp +'mV'
            self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, action, self.Action_Num_Normal, print_info)
        else:
            self.textBroswerPrintRealTime('XQ_LockDither must < 100mV')
    def YI_LockDither_Set_cb(self, flag, Amp, print_info = [2, True, False]):
        if flag == 0:
            DitherAmp = self.YI_LockDither.text()
        else:
            DitherAmp = str(Amp)
        
        if float(DitherAmp) < 100:
            hex_buf = '0x'+f"{int(float(DitherAmp)):04X}"#转化为带0x的4位16进制数
            
            cmd_text = 'AA 04 F2 03 AA '+ str(hex_buf)[-2:]
            action = 'Set YI_LockDither: '+ DitherAmp +'mV'
            self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, action, self.Action_Num_Normal, print_info)
        else:
            self.textBroswerPrintRealTime('YI_LockDither must < 100mV')
    def YQ_LockDither_Set_cb(self, flag, Amp, print_info = [2, True, False]):
        if flag == 0:
            DitherAmp = self.YQ_LockDither.text()
        else:
            DitherAmp = str(Amp)
        
        if float(DitherAmp) < 100:
            hex_buf = '0x'+f"{int(float(DitherAmp)):04X}"#转化为带0x的4位16进制数
            
            cmd_text = 'AA 04 F2 04 AA '+ str(hex_buf)[-2:]
            action = 'Set YQ_LockDither: '+ DitherAmp +'mV'
            self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, action, self.Action_Num_Normal, print_info)
        else:
            self.textBroswerPrintRealTime('YQ_LockDither must < 100mV')
    def XP_LockDither_Set_cb(self, flag, Amp1, Amp2, print_info = [2, True, False]):
        if flag == 0:
            DitherAmp = self.XPhaseDither_I.text()
        else:
            DitherAmp =str(Amp1)
        
        if float(DitherAmp) < 100:
            hex_buf = '0x'+f"{int(float(DitherAmp)):04X}"#转化为带0x的4位16进制数
            
            cmd_text = 'AA 04 F2 05 AA '+ str(hex_buf)[-2:]
            action = 'Set '+self.Name_channel_list[5]+'_LockDither_I: '+ DitherAmp +'mV'
            self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, action, self.Action_Num_Normal, print_info)
        else:
            self.textBroswerPrintRealTime('YQ_LockDither must < 100mV')


        if flag == 0:
            DitherAmp = self.XPhaseDither_Q.text()
        else:
            DitherAmp = str(Amp2)        
        
        if float(DitherAmp) < 100:
            hex_buf = '0x'+f"{int(float(DitherAmp)):04X}"#转化为带0x的4位16进制数
            
            cmd_text = 'AA 04 F2 05 AB '+ str(hex_buf)[-2:]
            action = 'Set '+self.Name_channel_list[5]+'_LockDither_Q: '+ DitherAmp +'mV\n'
            self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, action, self.Action_Num_Normal, print_info)
        else:
            self.textBroswerPrintRealTime('YQ_LockDither must < 100mV\n')     
    def YP_LockDither_Set_cb(self, flag, Amp1, Amp2, print_info = [2, True, False]):
        if flag == 0:
            DitherAmp = self.YPhaseDither_I.text()
        else:
            DitherAmp = str(Amp1)        
        
        if float(DitherAmp) < 100:
            hex_buf = '0x'+f"{int(float(DitherAmp)):04X}"#转化为带0x的4位16进制数
            
            cmd_text = 'AA 04 F2 06 AA '+ str(hex_buf)[-2:]
            action = 'Set '+self.Name_channel_list[6]+'_LockDither_I: '+ DitherAmp +'mV'
            self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, action, self.Action_Num_Normal, print_info)
        else:
            self.textBroswerPrintRealTime('YQ_LockDither must < 100mV')
            
        if flag == 0:
            DitherAmp = self.YPhaseDither_Q.text()
        else:
            DitherAmp = str(Amp2)         
        
        if float(DitherAmp) < 100:
            hex_buf = '0x'+f"{int(float(DitherAmp)):04X}"#转化为带0x的4位16进制数
            
            cmd_text = 'AA 04 F2 06 AB '+ str(hex_buf)[-2:]
            action = 'Set '+self.Name_channel_list[6]+'_LockDither_Q: '+ DitherAmp +'100mV\n'
            self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, action, self.Action_Num_Normal, print_info)
        else:
            self.textBroswerPrintRealTime('YQ_LockDither must < 50mV\n')
            
    #读取 导数       
    def XI_FirdtDeri_Rd_cb(self, show_flag = [2,True,True]):    
        buf = '' 
        cmd_text = 'AA 84 F3 01 AA AA'
        Action = 'Rd XI_FirstDerivative/读取XI一阶导数 '
        Value = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, show_flag)
        #取hex值的最高位判断导数的正负
        flag = int( int(Value,16)>>15 )
        if flag == 0:
            buf = str(float(round( int(Value, 16)/100.0, 5)))[:4]
        elif flag ==1:
            buf = str(float(round( 0 - (int(Value,16) & 0x7FFF)/100.0, 5)))[:5]

        if show_flag[1] == True:
            self.XI_FirstDeri.setText(buf)
            self.textBroswerPrintRealTime('XI_FirstDerivative: '+buf)
            self.textBroswerPrintRealTime('')       
        return buf    
    def XQ_FirdtDeri_Rd_cb(self, show_flag = [2,True,True]):      
        cmd_text = 'AA 84 F3 02 AA AA'
        buf = ''     
        Action = 'Rd XQ_FirstDerivative/读取XQ一阶导数 '
        Value = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, show_flag)
        #取hex值的最高位判断导数的正负
        flag = int( int(Value,16)>>15 )
        if flag == 0:
            buf = str(float(round( int(Value, 16)/100.0, 5)))[:4]
        elif flag ==1:
            buf = str(float(round( 0 - (int(Value,16) & 0x7FFF)/100.0, 5)))[:5]

        if show_flag[1] == True:
            self.XQ_FirstDeri.setText(buf)
            self.textBroswerPrintRealTime('XQ_FirstDerivative: '+buf)
            self.textBroswerPrintRealTime('') 
        return buf    
    def YI_FirdtDeri_Rd_cb(self, show_flag = [2,True,True]):      
        cmd_text = 'AA 84 F3 03 AA AA'
        buf = ''       
        Action = 'Rd YI_FirstDerivative/读取YI一阶导数 '
        Value = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, show_flag)
        #取hex值的最高位判断导数的正负
        flag = int( int(Value,16)>>15 )
        if flag == 0:
            buf = str(float(round( int(Value, 16)/100.0, 5)))[:4]
        elif flag ==1:
            buf = str(float(round( 0 - (int(Value,16) & 0x7FFF)/100.0, 5)))[:5]

        if show_flag[1] == True:
            self.YI_FirstDeri.setText(buf)
            self.textBroswerPrintRealTime('YI_FirstDerivative: '+buf)
            self.textBroswerPrintRealTime('')  
        return buf           
    def YQ_FirdtDeri_Rd_cb(self, show_flag = [2,True,True]):      
        cmd_text = 'AA 84 F3 04 AA AA'
        buf = '' 
        Action = 'Rd YQ_FirstDerivative/读取YQ一阶导数 '
        Value = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, show_flag)
        #取hex值的最高位判断导数的正负
        flag = int( int(Value,16)>>15 )
        if flag == 0:
            buf = str(float(round( int(Value, 16)/100.0, 5)))[:4]
        elif flag ==1:
            buf = str(float(round( 0 - (int(Value,16) & 0x7FFF)/100.0, 5)))[:5]

        if show_flag[1] == True:
            self.YQ_FirstDeri.setText(buf)
            self.textBroswerPrintRealTime('YQ_FirstDerivative: '+buf)
            self.textBroswerPrintRealTime('')  
        return buf    
    def XP_SecondDeri_Rd_cb(self, show_flag = [2,True,True]):      
        cmd_text = 'AA 84 F3 05 AA AA'
        buf = '' 
        Action = 'Rd XP_SecondDerivative/读取XP锁定二阶导数 '
        Value = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, show_flag)
        #取hex值的最高位判断导数的正负
        flag = int( int(Value,16)>>15 )
        if flag == 0:
            buf = str(float(round( int(Value, 16)/100.0, 5)))[:4]
        elif flag ==1:
            buf = str(float(round( 0 - (int(Value,16) & 0x7FFF)/100.0, 5)))[:5]

        if show_flag[1] == True:    
            self.XP_SecondDeri.setText(buf)  
            self.textBroswerPrintRealTime('XP_SecondDerivative: '+buf)
            self.textBroswerPrintRealTime('')     
        return buf 
    def YP_SecondDeri_Rd_cb(self, show_flag = [2,True,True]):
        cmd_text = 'AA 84 F3 06 AA AA'
        buf = '' 
        Action = 'Rd YP_SecondDerivative/读取YP锁定二阶导数 '
        Value = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, show_flag)
        #取hex值的最高位判断导数的正负
        flag = int( int(Value,16)>>15 )
        if flag == 0:
            buf = str(float(round( int(Value, 16)/100.0, 5)))[:4]
        elif flag ==1:
            buf = str(float(round( 0 - (int(Value,16) & 0x7FFF)/100.0, 5)))[:5]
        
        if show_flag[1] == True:
            self.YP_SecondDeri.setText(buf)
            self.textBroswerPrintRealTime('YP_SecondDerivative: '+buf)
            self.textBroswerPrintRealTime('')  
        return buf
    
    def XI_FirdtDeri_Do_cb(self): #执行导数空跑，获取此次的采集结果的上报
        dither = self.run_dither.text()
        dither = f"{int(dither):02X}"
        cmd_text = 'AA 01 FC 01 AA '+ str(dither)
        action = '获取XI当前一阶导数值, Dither: '+str(dither)+'mV'
        self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, action, self.Action_Num_Normal,self.print_info_fast)
        self.XI_FirdtDeri_Rd_cb(self.print_info_fast)         
    def XQ_FirdtDeri_Do_cb(self):
        dither = float(self.run_dither.text())
        dither = f"{int(dither):02X}"
        cmd_text = 'AA 01 FC 02 AA '+ str(dither)
        
        action = '获取XQ当前一阶导数值, Dither: '+str(dither)+'mV'
        self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, action, self.Action_Num_Normal,self.print_info_fast)
        self.XQ_FirdtDeri_Rd_cb(self.print_info_fast)
    def YI_FirdtDeri_Do_cb(self):
        dither = float(self.run_dither.text())
        dither = f"{int(dither):02X}"
        cmd_text = 'AA 01 FC 03 AA '+ str(dither)
        action = '获取YI当前一阶导数值, Dither: '+str(dither)+'mV'
        self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, action, self.Action_Num_Normal,self.print_info_fast)
        self.YI_FirdtDeri_Rd_cb(self.print_info_fast)         
    def YQ_FirdtDeri_Do_cb(self):
        dither = float(self.run_dither.text())
        dither = f"{int(dither):02X}"
        cmd_text = 'AA 01 FC 04 AA '+ str(dither)
        action = '获取YQ当前一阶导数值, Dither: '+str(dither)+'mV'
        self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, action, self.Action_Num_Normal,self.print_info_fast)
        self.YQ_FirdtDeri_Rd_cb(self.print_info_fast)
     
    def XP_SecondDeri_Do_cb(self):
        cmd_text = 'AA 01 FB 01 AA AA'
        action = '获取XP当前二阶导数'
        self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, action, self.Action_Num_Normal,self.print_info_fast)
        self.XP_SecondDeri_Rd_cb(self.print_info_fast)
            
    def YP_SecondDeri_Do_cb(self):
        cmd_text = 'AA 01 FB 02 AA AA'

        action = '获取YP当前二阶导数'
        self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, action, self.Action_Num_Normal,self.print_info_fast)
        self.YP_SecondDeri_Rd_cb(self.print_info_fast)

    #'0x'+f"{int(float(self.XP_SecondDeri.text())*1000):04X}"   十进制转化为0x****的hex值
    def XP_LockingThresholdOffset_Rd_cb(self):
        cmd_text = 'AA 84 F1 B5 AA AA'
        buf = '' 
        Action = 'Rd XP_LockingThresholdOffset/读取XP锁定门限偏移量'    
        Value = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, self.print_info_fast)
        #取hex值的最高位判断导数的正负
        flag = int( int(Value,16)>>15 )
        if flag == 0:
            buf = str(float(round( int(Value, 16)/100.0, 5)))[:4]
        elif flag ==1:
            buf = str(float(round( 0 - (int(Value,16) & 0x7FFF)/100.0, 5)))[:5]  
        self.XP_LockingThresholdOffset.setText(buf)
        self.textBroswerPrintRealTime('Rd XP_LockingThresholdOffset: '+buf+'mV\n')          
    def YP_LockingThresholdOffset_Rd_cb(self):
        cmd_text = 'AA 84 F1 B6 AA AA'
        buf = ''       
        Action = 'Rd YP_LockingThresholdOffset/读取YP锁定门限偏移量'    
        Value = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, self.print_info_fast)
        #取hex值的最高位判断导数的正负
        flag = int( int(Value,16)>>15 )
        if flag == 0:
            buf = str(float(round( int(Value, 16)/100.0, 5)))[:4]
        elif flag ==1:
            buf = str(float(round( 0 - (int(Value,16) & 0x7FFF)/100.0, 5)))[:5]  
        self.YP_LockingThresholdOffset.setText(buf)
        self.textBroswerPrintRealTime('Rd YP_LockingThresholdOffset: '+buf+'mV\n')      
    def XP_LockingThresholdOffset_Set_cb(self):
        
        buf = ''
        hex_buf = '' 
        text = ''  
        Offset = self.XP_LockingThresholdOffset.text()
        if (Offset == ''):
            text = 'XP_LockingThresholdOffset can`t be empty\n'
            self.textBroswerPrintRealTime(text)
        elif float(Offset) < -50 or float(Offset) > 50:
            text = 'XP_LockingThresholdOffset must be: -50 < Offset < 50\n'
            self.textBroswerPrintRealTime(text)
        else:
            if float(Offset) < 0:
                buf = abs(int( float(Offset)*100.0 ) )
                hex_buf = ('0x'+f"{ (buf|0x8000) :04X}") #最高位置1
            else:
                hex_buf = '0x'+f"{int( float(Offset)*100 ):04X}" 
            
            cmd_text = 'AA 04 F1 B5 '+ str(hex_buf)[-4:-2] +' '+ str(hex_buf)[-2:]
            Action = 'Set XP_LockingThresholdOffset: '+ str(float(Offset)) +'mV'
            self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, Action, self.Action_Num_Normal, self.print_info_fast)
            self.textBroswerPrintRealTime('')        
    def YP_LockingThresholdOffset_Set_cb(self):
        
        buf = ''
        hex_buf = '' 
        text = ''  
        Offset = self.YP_LockingThresholdOffset.text()
        if (Offset == ''):
            text = 'YP_LockingThresholdOffset can`t be empty\n'
            self.textBroswerPrintRealTime(text)
        elif float(Offset) < -50 or float(Offset) > 50:
            text = 'YP_LockingThresholdOffset must be: -50 < Offset < 50\n'
            self.textBroswerPrintRealTime(text)
        else:
            if float(Offset) < 0:
                buf = abs(int( float(Offset)*100.0 ) )
                hex_buf = ('0x'+f"{ (buf|0x8000) :04X}") #最高位置1
            else:
                hex_buf = '0x'+f"{int( float(Offset)*100 ):04X}" 
            
            cmd_text = 'AA 04 F1 B6 '+ str(hex_buf)[-4:-2] +' '+ str(hex_buf)[-2:]
            Action = 'Set YP_LockingThresholdOffset: '+ str(float(Offset)) +'mV'
            self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, Action, self.Action_Num_Normal, self.print_info_fast)
            self.textBroswerPrintRealTime('')

    def XP_LockingThreshold_Rd_cb(self):
        cmd_text = 'AA 84 F1 A5 AA AA'
        Value_buf = ''     
        Action = 'Rd XP_LockingThreshold/读取XP锁定门限'    
        Value = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, self.print_info_fast)
        Value_buf = str(float(round( int(Value, 16)/100.0, 5)))[:4]
        self.XP_LockingThreshold.setText(Value_buf)
        self.textBroswerPrintRealTime('Read XP_LockingThreshold: '+Value_buf+'mV\n')              
    def YP_LockingThreshold_Rd_cb(self):
        
        cmd_text = 'AA 84 F1 A6 AA AA'
        Value_buf = '' 
        Action = 'Rd YP_LockingThreshold/读取YP锁定门限'    
        Value = self.SerialPortB_SendHexCMD_SelPrint_GetResult_cb(cmd_text, Action, self.Action_Num_Normal, self.print_info_fast)
        Value_buf = str(float(round( int(Value, 16)/100.0, 5)))[:4]
        self.YP_LockingThreshold.setText(Value_buf)
        self.textBroswerPrintRealTime('Read YP_LockingThreshold: '+Value_buf+'mV\n')   
    def XP_LockingThreshold_Set_cb(self):
        
        LockingThreshold = self.XP_LockingThreshold.text()
        
        if float(LockingThreshold) > 0.01 and float(LockingThreshold) < 300:
            
            hex_buf = '0x'+f"{int(float(LockingThreshold)*100):04X}"#转化为带0x的4位16进制数
            cmd_text = 'AA 04 F1 A5 '+ str(hex_buf)[-4:-2]+' '+ str(hex_buf)[-2:]
            Action = 'Set XP_LockingThreshold: '+ LockingThreshold +'mV'
            self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, Action, self.Action_Num_Normal, self.print_info_fast)
        else:
            self.textBroswerPrintRealTime('XP_LockingThreshold must be: 0.01 < Threshold < 300mV')
            self.textBroswerPrintRealTime('Set XP_LockingThreshold Fail' +self.Time_text())
        self.textBroswerPrintRealTime('')
    def YP_LockingThreshold_Set_cb(self):
 
        LockingThreshold = self.YP_LockingThreshold.text()
        
        if float(LockingThreshold) > 0.01 and float(LockingThreshold) < 300:
            
            hex_buf = '0x'+f"{int(float(LockingThreshold)*100):04X}"#转化为带0x的4位16进制数
            cmd_text = 'AA 04 F1 A6 '+ str(hex_buf)[-4:-2]+' '+ str(hex_buf)[-2:]

            Action = 'Set YP_LockingThreshold: '+ LockingThreshold +'mV'
            self.SerialPortB_SendHexCMD_SelPrint_CheckDone_cb(cmd_text, Action, self.Action_Num_Normal, self.print_info_fast)
        else:
            self.textBroswerPrintRealTime('YP_LockingThreshold must be: 0.01 < Threshold < 300mV')
            self.textBroswerPrintRealTime('Set YP_LockingThreshold Fail'+self.Time_text())
        self.textBroswerPrintRealTime('')

    def XI_LockCalibration_cb(self):

        cmd_text = ''
        report_text1 = ''
        report_text2 = ''
        
        DA_Step = int(self.DA_Step.text())


        cmd_text = 'AA 01 FC 05 '+str(f"{DA_Step:04X}")[0:2]+' '+str(f"{DA_Step:04X}")[2:4]
        report_text1 = 'XI_LockCalibration and SaveData'
        report_text2 = '遍历9个DA获取XI一阶导数曲线'
      
        action = report_text1+'/'+ report_text2
        
        print_info_buf = ['']*3
        print_info_buf[0] = 20  #标记数据的个数
        print_info_buf[1] = self.print_info_fast[1]
        print_info_buf[2] = self.print_info_fast[2]        
        #传输 参数
        self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_LockCalibration, print_info_buf, self.Rx_Array, '', self.DoLocking_Flag)
        #启动串口子线程
        # self.Uart.start()
        #启动轮询线程, 包含了SendCmd和数据处理
        self.LongTimeCmd_QThread.start()
    def XQ_LockCalibration_cb(self):

        cmd_text = ''
        report_text1 = ''
        report_text2 = ''
        DA_Step = int(self.DA_Step.text())
        cmd_text = 'AA 01 FC 06 '+str(f"{DA_Step:04X}")[0:2]+' '+str(f"{DA_Step:04X}")[2:4]
        report_text1 = 'XQ_LockCalibration and SaveData'
        report_text2 = '遍历9个DA获取XQ一阶导数曲线'
      
        action = report_text1+'/'+ report_text2
        
        print_info_buf = ['']*3
        print_info_buf[0] = 20  #标记数据的个数
        print_info_buf[1] = self.print_info_fast[1]
        print_info_buf[2] = self.print_info_fast[2]        
        #传输 参数
        self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_LockCalibration, print_info_buf, self.Rx_Array, '', self.DoLocking_Flag)
        #启动串口子线程
        # self.Uart.start()
        #启动轮询线程, 包含了SendCmd和数据处理
        self.LongTimeCmd_QThread.start()
    def YI_LockCalibration_cb(self):

        cmd_text = ''
        report_text1 = ''
        report_text2 = ''

        DA_Step = int(self.DA_Step.text())
        cmd_text = 'AA 01 FC 07 '+str(f"{DA_Step:04X}")[0:2]+' '+str(f"{DA_Step:04X}")[2:4]
        report_text1 = 'YI_LockCalibration and SaveData'
        report_text2 = '遍历9个DA获取YI一阶导数曲线'
      
        action = report_text1+'/'+ report_text2
        
        print_info_buf = ['']*3
        print_info_buf[0] = 20  #标记数据的个数
        print_info_buf[1] = self.print_info_fast[1]
        print_info_buf[2] = self.print_info_fast[2]        
        #传输 参数
        self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_LockCalibration, print_info_buf, self.Rx_Array, '', self.DoLocking_Flag)
        #启动串口子线程
        # self.Uart.start()
        #启动轮询线程, 包含了SendCmd和数据处理
        self.LongTimeCmd_QThread.start()       
    def YQ_LockCalibration_cb(self):

        cmd_text = ''
        report_text1 = ''
        report_text2 = ''
        
        DA_Step = int(self.DA_Step.text())


        cmd_text = 'AA 01 FC 08 '+str(f"{DA_Step:04X}")[0:2]+' '+str(f"{DA_Step:04X}")[2:4]
        report_text1 = 'YQ_LockCalibration and SaveData'
        report_text2 = '遍历9个DA获取YQ一阶导数曲线'
      
        action = report_text1+'/'+ report_text2
        
        print_info_buf = ['']*3
        print_info_buf[0] = 20  #标记数据的个数
        print_info_buf[1] = self.print_info_fast[1]
        print_info_buf[2] = self.print_info_fast[2]        
        #传输 参数
        self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_LockCalibration, print_info_buf, self.Rx_Array, '', self.DoLocking_Flag)
        #启动串口子线程
        # self.Uart.start()
        #启动轮询线程, 包含了SendCmd和数据处理
        self.LongTimeCmd_QThread.start()  
                        
    def XP_LockCalibration_cb(self):

        cmd_text = ''
        report_text1 = ''
        report_text2 = ''
        
        DA_Step = int(self.DA_Step.text())


        cmd_text = 'AA 01 FB 03 '+str(f"{DA_Step:04X}")[0:2]+' '+str(f"{DA_Step:04X}")[2:4]
        report_text1 = 'X_LockCalibration and SaveData'
        report_text2 = '遍历9个DA获取XP二阶导数曲线'
      
        action = report_text1+'/'+ report_text2
        
        print_info_buf = ['']*3
        print_info_buf[0] = 20  #标记数据的个数
        print_info_buf[1] = self.print_info_fast[1]
        print_info_buf[2] = self.print_info_fast[2]        
        #传输 参数
        self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_LockCalibration, print_info_buf, self.Rx_Array, '', self.DoLocking_Flag)
        #启动串口子线程
        # self.Uart.start()
        #启动轮询线程, 包含了SendCmd和数据处理
        self.LongTimeCmd_QThread.start()           
    def YP_LockCalibration_cb(self):

        cmd_text = ''
        report_text1 = ''
        report_text2 = ''
        
        DA_Step = int(self.DA_Step.text())

        cmd_text = 'AA 01 FB 04 '+str(f"{DA_Step:04X}")[0:2]+' '+str(f"{DA_Step:04X}")[2:4]

        report_text1 = 'Y_LockCalibration and SaveData'
        report_text2 = '遍历9个DA获取YP二阶导数曲线'
      
        action = report_text1+'/'+ report_text2
        
        print_info_buf = ['']*3
        print_info_buf[0] = 20  #标记数据的个数
        print_info_buf[1] = self.print_info_fast[1]
        print_info_buf[2] = self.print_info_fast[2]        
        #传输 参数
        self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_LockCalibration, print_info_buf, self.Rx_Array, '', self.DoLocking_Flag)
        #启动串口子线程
        # self.Uart.start()
        #启动轮询线程, 包含了SendCmd和数据处理
        self.LongTimeCmd_QThread.start()  
            

    def Triggle_Uart_QThreadstop(self):
        self.Uart.Stop()
        self.QThread_Run_Flag = False
        
    def Triggle_Uart_QThreadstart(self, flag = False):
        if flag == True:
            self.COM_ClearBuffer()
        self.Uart.start()
    def Triggle_Uart_Clear(self):
        self.Uart.Clear_DataBuffer()
    #函数 调用串口，进行 占用长时间的写操作，返回：该操作的完成状态
    def SerialPortB_SendHexCMD_PrintTx_WaittingToCheckDone_cb(self, cmd, Action='', Action_Num=999, show_flag=[2,True,True]):#传输指令/Rx需读取次数/是否打印TxRX信息的标志位

        #注意：RxDataNum = 999，则表示进行占用长时间的写操作
        cmd = re.sub(r"\s+", "", cmd).upper()  # 去除空格
        
        if show_flag[1] == True:
            self.textBroswerPrintRealTime(Action)
            
        self.LongTimeCmd_QThread.Uart.Uart_Rx_ThreadStart()
        sleep(0.001)                 
          
        self.LongTimeCmd_QThread.Uart.Tx_HexSignal.emit(cmd, Action_Num, show_flag)#触发自定义信号,启动Uart_Tx并判断是否成功发送,1:返回信息进入数据进行保存
        

    def CDM_SN_Save_cb(self):
        self.setting_CDM.setValue("setup/CDM_SN", self.CDM_SN.text())   
        self.textBroswerPrintRealTime('Save CDM_SN: '+self.CDM_SN.text())
    def CDM_T_WL_Save_cb(self):
        self.setting_CDM.setValue("setup/T0", self.CDM_T0.text())   
        self.textBroswerPrintRealTime('Save CDM_T0: '+self.CDM_T0.text())
        self.setting_CDM.setValue("setup/WL0", self.CDM_WL0.text())   
        self.textBroswerPrintRealTime('Save CDM_WL0: '+self.CDM_WL0.text())

    def update_WL_Temperature(self):
        if self.LinkToEquipment.isChecked() == True:
            self.setting_equipment.sync()
            WL0_buf = self.setting_equipment.value('setup_ITLA/WL0')
            self.setting_CDM.setValue("setup/WL0", str(WL0_buf)[0:8]) 
            
            T0_buf = self.setting_equipment.value('setup_TEC/T0')
            self.setting_CDM.setValue("setup/T0", str(T0_buf)[0:4])  
            
            self.CDM_T0_buf = self.setting_CDM.value("setup/T0")
            self.CDM_T0.setText(str(self.CDM_T0_buf)) 
            self.CDM_WL0_buf = round(float(self.setting_CDM.value("setup/WL0")),1)
            self.CDM_WL0.setText(str(self.CDM_WL0_buf)) 

        else:
            self.CDM_T0_buf = self.setting_CDM.value("setup/T0")
            self.CDM_T0.setText(str(self.CDM_T0_buf)) 
            self.CDM_WL0_buf = round(float(self.setting_CDM.value("setup/WL0")),1)
            self.CDM_WL0.setText(str(self.CDM_WL0_buf))             
         
    def FindPoint_cb(self):#找点

        self.textBroswerPrintRealTime(self.Time_text())
        cmd_text = 'AA 00 FF AA AA AA' #MIN MIN QUAD or MaxMaxMax
        action = 'Start to findpoint, 共220个步骤...'
        
        #传输 参数
        self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_FindPoint, self.print_info_fast, self.Rx_Array, self.FindPoint_Record_length, self.DoLocking_Flag)
        #启动串口子线程
        # self.Uart.start()
        #启动轮询线程, 包含了SendCmd和数据处理
        self.FindPoint_TimeStart = self.Time_text()
        self.LongTimeCmd_QThread.start()
    def FindPoint_Timecalculate_cb(self, OverTime):
        
        self.FindPoint_TimeOver = OverTime
        self.Time_calculate(self.FindPoint_TimeStart,self.FindPoint_TimeOver)

    def FindPoint_RecordSave_cb(self):
 
        #3种数组长度  26/20/30
        
        length = self.FindPoint_Record_length#顺序 I、Q、P、P_again

        #创建一个数组
        self.array_element_BitNum = ['']*20
        
        #计算一个数组 标记各元素内部的位数，传递给Urat
        self.array_element_BitNum[0] = 1*6#回复原指令
        #起始位置，平移 1个元素
        for i in range(16):
            self.array_element_BitNum[i+1] = length*6 #每个元素一次性读取  WordNum*6个字节的长数据                    
        self.array_element_BitNum[16+1] = 16*6
        self.array_element_BitNum[16+2] = 6*6
        self.array_element_BitNum[16+3] = 1*6#所有数据接收完成，'AFAF'
        
        self.Uart.Rx_data_WordNum_array.emit(self.array_element_BitNum)#传递给Uart
        
        self.LongTimeCmd_QThread.Record_Plot_En.emit(self.FindPointRecord_Plot.isChecked())#传递给LongTimeCmd_QThread

        #将设备信息转移到当前config_CDM.ini等待调用
        self.update_WL_Temperature()
    
        self.Refresh_COM_settings(False)

        cmd_text = 'AA 87 F1 AA AA AA'#指令
        action = 'FindPoint_Record_Save...'
        #传输 参数
        print_info_buf = ['']*3
        
        print_info_buf[0] = 20  #标记数据的个数
        print_info_buf[1] = self.print_info_fast[1]
        print_info_buf[2] = self.print_info_fast[2]
        
        self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_FindPointRecrodSave, print_info_buf, self.Rx_Array, self.FindPoint_Record_length, self.DoLocking_Flag)
        #启动串口子线程
        # self.Uart.start()
        #启动轮询线程, 包含了SendCmd和数据处理
        self.LongTimeCmd_QThread.start() 
        
    def Refresh_COM_settings(self, flag, type = ''):
        #这个函数可以去掉
        if flag == True:
            self.Uart.Rx_data_WordNumSel = True     #恢复  RX标志位
            self.Uart.custom_serial.timeout = 0.01

        else:
            self.Uart.Rx_data_WordNumSel = False    #设置  RX标志位
            if type == 'FindPoint':
                self.Uart.custom_serial.timeout = 0.05
            elif type == 'LockPoint':
                self.Uart.custom_serial.timeout = 0.05
            
    def COM_ClearBuffer(self):
        self.Uart.Clear_DataBuffer()
        print(self.Rx_Array_buf,'清空串口缓冲区')
        self.textBroswerPrintRealTime('清空串口缓冲区')
      
    def LockingPoint_Run_cb(self):

        cmd_text = ''
        report_text1 = ''
        report_text2 = ''
        LockCycle_Target = 0
           
        self.LockPoint_Run.setEnabled(False)  # 灰色
        self.LockPoint_Stop.setEnabled(True)  
        
        Flag_Mode = 0#全部通道锁定还是只锁定IQ
        
        try:
            if int(self.LockCycle_Value.text()) >= 1 and int(self.LockCycle_Value.text()) <= 1e8:
                LockCycle_Target = int(self.LockCycle_Value.text())
            elif int(self.LockCycle_Value.text()) > 1e8:
                self.DoLocking_Flag = False
                self.textBroswerPrintRealTime('LockCycle shuold less than 1e8+1')
            else:
                self.DoLocking_Flag = False
                self.textBroswerPrintRealTime('LockCycle is no right')
        except:
            LockCycle_Target = 0
            self.DoLocking_Flag = False
            self.textBroswerPrintRealTime('LockCycle is no right')
                
                
        report_text1 = 'All_Ch_Lock Loop'
        report_text2 = '所有MZ 循环锁定'    
        self.CalibrateLocking_Flag = False
                                      
        if self.Lock_XY_ALL.isChecked() == True and self.LockRecord_EnSave.isChecked() == True and LockCycle_Target > 0:
            cmd_text = 'AA 01 F1 01 10 01'
            self.setting_CDM.setValue('setup/LockRecord_EnSave',True)
            FileName = self.LockErr_CsvSetUp()
            FileName_HeaterR = self.HeaterR_CsvSetUp()
            self.DoLocking_Flag = True
            
            Flag_Mode = 0

        elif self.Lock_XY_ALL.isChecked() == True and self.LockRecord_EnSave.isChecked() == False and LockCycle_Target > 0:
            cmd_text = 'AA 01 F1 01 10 00'
            self.setting_CDM.setValue('setup/LockRecord_EnSave',False)
            FileName = ''
            FileName_HeaterR = '' 
            self.DoLocking_Flag = True
            Flag_Mode = 0
            
        # elif self.Lock_XY_IQ.isChecked() == True and self.LockRecord_EnSave.isChecked() == False and LockCycle_Target > 0:
        #     self.setting_CDM.setValue('setup/LockRecord_EnSave',False)
        #     FileName = ''
        #     FileName_HeaterR = '' 
        #     self.DoLocking_Flag = True            
        #     Flag_Mode = 1


        if self.Record_DRVTemperature_EN.isChecked() == True and self.DoLocking_Flag == True:
            self.setting_CDM.setValue('setup/DRV_Temperature_SaveFlag',True)
        else:
            self.setting_CDM.setValue('setup/DRV_Temperature_SaveFlag',False)        


               
        # elif self.All_Lock_Always.isChecked() == False and self.All_Lock_X.isChecked() == True and self.All_Lock_Y.isChecked() == False:
        #     # cmd_text = 'AA 01 F1 02 AA AA'
        #     cmd_text = 'AA 01 F1 02 '+str(f"{LockCycle_Target:04X}")[0:2]+' '+str(f"{LockCycle_Target:04X}")[2:4]
        #     report_text1 = '\nLock X IQP Locking '
        #     report_text2 = 'X偏振态 IQP锁定 '
  
            
        # elif self.All_Lock_Always.isChecked() == False and self.All_Lock_X.isChecked() == False and self.All_Lock_Y.isChecked() == True:
        #     # cmd_text = 'AA 01 F1 03 AA AA'
        #     cmd_text = 'AA 01 F1 03 '+str(f"{LockCycle_Target:04X}")[0:2]+' '+str(f"{LockCycle_Target:04X}")[2:4]
        #     report_text1 = '\nLock Y IQP Locking '
        #     report_text2 = 'Y偏振态 IQP锁定 '

        if Flag_Mode == 0:#全部通道锁定
            #创建一个数组,分配各个元素的长度
            array_element_BitNum = ['']*5
            array_element_BitNum[0] = 1*6#cmd
            
            array_element_BitNum[1] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
            array_element_BitNum[2] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
            array_element_BitNum[3] = 6*(6+2) #每个元素一次性读取  WordNum*6个字节的长数据+ 一个EXPD_flag、一个EXPD ADC

            array_element_BitNum[4] = 1*6#所有数据接收完成，'AFAF'
            
            self.Uart.Rx_data_WordNum_array.emit(array_element_BitNum)#传递给Uart

            #传输 参数
            print_info_buf = ['']*3
            
            print_info_buf[0] = 20  #标记数据的个数:1*cmd+6*heaterDA+6*平均导数值+6*实时导数值+1*"AFAF"
            print_info_buf[1] = self.print_info_no[1]
            print_info_buf[2] = self.print_info_no[2]
            
            if self.DoLocking_Flag == True:
                self.Refresh_COM_settings(False,'LockPoint')#设置串口响应时间

                text = '\n'+report_text1+' begin... '+ report_text2+'开始... '
                self.textBroswerPrintRealTime(text)                  
                
                action = '\n'+report_text1+' begin.../'+ report_text2+'开始... '            

                self.Lock_TimeStart = str(self.Time_text())#记录开始锁定的时间
                self.textBroswerPrintRealTime('')
                self.textBroswerPrintRealTime('StartTime: '+self.Lock_TimeStart)
                self.textBroswerPrintRealTime('锁定中...')
                self.textBroswerPrintRealTime('')
                        
                self.LongTimeCmd_QThread.LockCycle_Target = LockCycle_Target
                self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_XY_Lock, print_info_buf, self.Rx_Array, self.FindPoint_Record_length, 
                                                    self.DoLocking_Flag, FileName, FileName_HeaterR, self.CalibrateLocking_Flag)
                
                self.LockState.setStyleSheet('background-color:rgb(0, 255, 0)')               
                #启动轮询线程, 包含了SendCmd和数据处理
                self.LongTimeCmd_QThread.start()  
            else:
                self.LockPoint_Run.setEnabled(True)  
                self.LockPoint_Stop.setEnabled(False)  # 灰色     
                
        elif Flag_Mode == 1:   
            self.IQLockPoint_cb()       
   
    def LockPoint_cycle_show(self, num): 
        self.LockPoint_cycle =  num              
        self.LockState.setText(str(num))#在LockeState控件上，更新锁定次数
    def LockPoint_Info_show(self,array):
        #刷新一次DAC值，确保为最新工作点+导数
        self.DaShow_channel_list[1].setText(array[1][8:12])
        self.DaShow_channel_list[2].setText(array[1][12*1+8:12*1+12])
        self.DaShow_channel_list[5].setText(array[1][12*2+8:12*2+12])
        self.DaShow_channel_list[3].setText(array[1][12*3+8:12*3+12])
        self.DaShow_channel_list[4].setText(array[1][12*4+8:12*4+12])
        self.DaShow_channel_list[6].setText(array[1][12*5+8:12*5+12])        

        buf=['']*6
        
        # if self.setting_CDM.value('setup/LockRecord_EnSave') ==  True:
        #处理 回读的导数
        for i in range(6):
            try:
                Value = array[2][12*i+8:12*i+12]
                #取hex值的最高位判断导数的正负
                flag = int( int(Value,16)>>15 )
                if flag == 0:
                    buf[i] = str(float(round( int(Value, 16)/100.0, 5)))[:4]
                elif flag ==1:
                    buf[i] = str(float(round( 0 - (int(Value,16) & 0x7FFF)/100.0, 5)))[:5]   
            except:
                self.textBroswerPrintRealTime('数据出错')      
                   
        self.XI_FirstDeri.setText(buf[0])
        self.XQ_FirstDeri.setText(buf[1])
        self.XP_SecondDeri.setText(buf[2])
        
        self.YI_FirstDeri.setText(buf[3])
        self.YQ_FirstDeri.setText(buf[4])
        self.YP_SecondDeri.setText(buf[5])

        self.setting_CDM.setValue("LockPoint/LockPoint_XI", array[1][8:12])
        self.DaVolt_Show(1, self.Dahex_to_HeaterR_Volt(     array[1][8:12]), self.PushPull_BiasAmpVolt)
        
        self.setting_CDM.setValue("LockPoint/LockPoint_XQ", array[1][12*1+8:12*1+12])
        self.DaVolt_Show(2, self.Dahex_to_HeaterR_Volt(     array[1][12*1+8:12*1+12]), self.PushPull_BiasAmpVolt)
        
        self.setting_CDM.setValue("LockPoint/LockPoint_XP", array[1][12*2+8:12*2+12])
        self.DaVolt_Show(5, self.Dahex_to_HeaterR_Volt(     array[1][12*2+8:12*2+12]), self.PushPull_BiasAmpVolt)
        
        self.setting_CDM.setValue("LockPoint/LockPoint_YI", array[1][12*3+8:12*3+12])
        self.DaVolt_Show(3, self.Dahex_to_HeaterR_Volt(     array[1][12*3+8:12*3+12]), self.PushPull_BiasAmpVolt)
        
        self.setting_CDM.setValue("LockPoint/LockPoint_YQ", array[1][12*4+8:12*4+12])
        self.DaVolt_Show(4, self.Dahex_to_HeaterR_Volt(     array[1][12*4+8:12*4+12]), self.PushPull_BiasAmpVolt)
        
        self.setting_CDM.setValue("LockPoint/LockPoint_YP", array[1][12*5+8:12*5+12])
        self.DaVolt_Show(6, self.Dahex_to_HeaterR_Volt(     array[1][12*5+8:12*5+12]), self.PushPull_BiasAmpVolt)
        
        
        # self.LongTimeCmd_QThread.GUI_Refresh_flag = False
    def LockCycle_Sel_cb(self, flag):
        if flag == 'cycle':
            if self.Lock_Cycle.isChecked() == True:
                self.Lock_AlwaysRun.setChecked(False)  
        elif flag == 'always':    
            if self.Lock_AlwaysRun.isChecked() == True:
                self.Lock_Cycle.setChecked(False)             
                            
    def HeaterR_CsvSetUp(self):  
        #将设备信息转移到当前config_CDM.ini等待调用
        self.update_WL_Temperature()      
            
        CDM_SN = self.setting_CDM.value("setup/CDM_SN")
        self.CDM_T0_Value = self.setting_CDM.value("setup/T0")
        self.CDM_WL0_Value = round(float(round(float(self.setting_CDM.value("setup/WL0")),1)),1)      

        folder_path = './log/' + CDM_SN + '/' + CDM_SN +'_'+ str(self.CDM_T0_Value) +'c_'+ str(self.CDM_WL0_Value)+'/' + 'HeaterR'+ '/'
        if not os.path.exists(folder_path):

            os.makedirs(folder_path)
            # print("文件夹创建成功")
            # self.textBroswerPrintRealTime("文件夹创建成功")
        else:
            # print("文件夹已存在")
            # self.textBroswerPrintRealTime("文件夹已存在")
            None
            
        cycle = int(self.LockCycle_Value.text())
        # csv文件名称
        filename_HeaterR = folder_path + str(CDM_SN) +'_'+ str(self.CDM_T0_Value) +'c_'+ str(self.CDM_WL0_Value) + '_HeaterR_Record_'+str(cycle)+'次_'+ self.Time_text()+'.csv' 
                                        
        
        self.textBroswerPrintRealTime( '\nCSV创建完成, 保存路径:'+ folder_path ) 
        self.textBroswerPrintRealTime( 'filename: '+ re.sub(folder_path,'',filename_HeaterR) )

        header = ['XI_HeaterR_P','XI_HeaterR_N','XQ_HeaterR_P','XQ_HeaterR_N',
                'YI_HeaterR_P','YI_HeaterR_N','YQ_HeaterR_P','YQ_HeaterR_N',
                'XP_HeaterR_P','XP_HeaterR_N','YP_HeaterR_P','YP_HeaterR_N',
                'XI_HeaterR_P_Cur','XI_HeaterR_N_Cur','XQ_HeaterR_P_Cur','XQ_HeaterR_N_Cur',
                'YI_HeaterR_P_Cur','YI_HeaterR_N_Cur','YQ_HeaterR_P_Cur','YQ_HeaterR_N_Cur',
                'XP_HeaterR_P_Cur','XP_HeaterR_N_Cur','YP_HeaterR_P_Cur','YP_HeaterR_N_Cur',                  
                'XI_HeaterR_P_Vol','XI_HeaterR_N_Vol','XQ_HeaterR_P_Vol','XQ_HeaterR_N_Vol',
                'YI_HeaterR_P_Vol','YI_HeaterR_N_Vol','YQ_HeaterR_P_Vol','YQ_HeaterR_N_Vol',
                'XP_HeaterR_P_Vol','XP_HeaterR_N_Vol','YP_HeaterR_P_Vol','YP_HeaterR_N_Vol',                    
                'XI_HeaterR_Ppi','XQ_HeaterR_Ppi',
                'YI_HeaterR_Ppi','YQ_HeaterR_Ppi',
                'XP_HeaterR_Ppi','YP_HeaterR_Ppi','DRV_Temperature','Time']        
        #header数据存进CSV 
        with open(filename_HeaterR, 'a', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)
            # for i in data:#  write in CSV
            #     writer.writerow(i)
            csvfile.close()    
    
        return filename_HeaterR  
    def LockErr_CsvSetUp(self):
        #将设备信息转移到当前config_CDM.ini等待调用
        self.update_WL_Temperature()      
                
        CDM_SN = self.setting_CDM.value("setup/CDM_SN")
        self.CDM_T0_Value = self.setting_CDM.value("setup/T0")
        self.CDM_WL0_Value = round(float(self.setting_CDM.value("setup/WL0")),1)        

        folder_path = './log/' + CDM_SN + '/' + CDM_SN +'_'+ str(self.CDM_T0_Value) +'c_'+ str(self.CDM_WL0_Value)+'/' + 'Lock'+ '/'
        # print(folder_path)
        if not os.path.exists(folder_path):

            os.makedirs(folder_path)
            # print("文件夹创建成功")
            # self.textBroswerPrintRealTime("文件夹创建成功")
        else:
            # print("文件夹已存在")
            # self.textBroswerPrintRealTime("文件夹已存在")
            None
        
        cycle = int(self.LockCycle_Value.text())
        # csv文件名称
        filename = folder_path +'/'+str(CDM_SN) +'_'+ str(self.CDM_T0_Value) +'c_'+ str(self.CDM_WL0_Value) + '_LockPoint_Record_'+str(cycle)+'次_'+ self.Time_text()+'.csv' 

        self.textBroswerPrintRealTime('\nCSV保存路径: '+ folder_path ) 
        self.textBroswerPrintRealTime('filename: '+ re.sub(folder_path,'',filename))#去掉filename中的folder_path部分

        header = ['XI_DA','XI_err','XQ_DA','XQ_err','XP_DA','XP_err','YI_DA','YI_err','YQ_DA','YQ_err','YP_DA','YP_err','Time','PD_Res_flag','LockPoint_EXPD_ADC_Value']        
        #所有数据存进CSV
        # data = list(zip(*array_buf))  # 行列转换
        # write in DAdata   
        with open(filename, 'a', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)
            # for i in data:#  write in CSV
            #     writer.writerow(i)
            csvfile.close()    
    
        return filename   
    def LockPoint_Stop_cb(self):  
        #关闭串口 子线程
        self.textBroswerPrintRealTime('锁定准备停止... / Stopping Locking...')

        #将锁定 循环的条件： 锁定次数置0，终结锁定的循环
        # self.LongTimeCmd_QThread.LockCycle = 0
        self.LongTimeCmd_QThread.LockCycle_Target = 0
        self.DoLocking_Flag = False
        self.CalibrateLocking_Flag = False
    def LockPoint_StopDone_cb(self,num):  
        self.DoLocking_Flag = False
        self.LockPoint_Run.setEnabled(True)  
        self.LockPoint_Stop.setEnabled(False)  # 灰色   
        
        self.Refresh_6ch_HeaterDA()  
        self.textBroswerPrintRealTime('') 
        self.textBroswerPrintRealTime('Loocking_Stop, Loocking_Num: '+str(num)) 
        self.Lock_TimeOver = str(self.Time_text())#记录开始锁定的时间 
        self.textBroswerPrintRealTime('锁定已停止/Locking Over') 

        buf = self.Time_calculate(self.Lock_TimeStart, self.Lock_TimeOver)
        self.textBroswerPrintRealTime('OverTime: '+self.Lock_TimeOver+', '+buf)
        self.LockState.setText('') 
        if self.CalibrateLocking_Flag == False:
            self.LockState.setStyleSheet('background-color:gray')   

    def Time_calculate(self, TimeStart, TimeOver, flag = True):
        # 创建两个时间实例
        # time1 = datetime(2023, 3, 15, 12, 0)  # 2023年3月15日 12:00
        # time2 = datetime(2023, 3, 16, 14, 30) # 2023年3月16日 14:30
        A1 = int(TimeStart[0:4])
        A2 = int(TimeStart[5:7])
        A3 = int(TimeStart[8:10])
        A4 = int(TimeStart[11:13])
        A5 = int(TimeStart[14:16])
        A6 = int(TimeStart[17:19])
        time1 = datetime.datetime(A1, A2, A3, A4, A5, A6) 
        A1 = int(TimeOver[0:4])
        A2 = int(TimeOver[5:7])
        A3 = int(TimeOver[8:10])
        A4 = int(TimeOver[11:13])
        A5 = int(TimeOver[14:16])
        A6 = int(TimeOver[17:19])        
        time2 = datetime.datetime(A1, A2, A3, A4, A5, A6)    
        
        # 计算时间差
        time_difference = time2 - time1
        # 输出时间差
        # print(time_difference)  # 输出的结果将是一个timedelta对象
        # 如果需要以秒为单位输出时间差
        total_seconds = time_difference.total_seconds()
        if flag == True:
            self.textBroswerPrintRealTime(f"Total TimeConsumption: {total_seconds}s")   
        return f"Total TimeConsumption: {total_seconds}s"  

    def EXPD_IQLock_Alignemet_cb(self):#IQ锁定 相位对齐

        cmd_text = 'AA 01 F8 A1 AA AA'
        action = '@EXPD, IQLock_Alignemet doing...'

        #传输 参数
        self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_IQAlignment, self.print_info_fast, self.Rx_Array, '', self.DoLocking_Flag)
        #启动串口子线程
        # self.Uart.start()
        #启动轮询线程, 包含了SendCmd和数据处理
        self.LongTimeCmd_QThread.start()          
    def IQLockPoint_cb(self):
        # 判断串口是否已经连接IQLockPoint
        if self.SerialPort_CheckConnect() == True:    
     
            if self.PD_SEL.isChecked() == False: 
                cmd_text = 'AA 01 F4 00 AA AA'
                action = '@EXPD, IQ Lockong...'

                #传输 参数
                self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_IQLock, self.print_info_fast, self.Rx_Array, '', self.DoLocking_Flag)
                
                #启动串口子线程
                # self.Uart.start()
                
                self.textBroswerPrintRealTime(self.Time_text())  
                
                #启动轮询线程, 包含了SendCmd和数据处理
                self.LongTimeCmd_QThread.start()                        
                                    
            elif self.PD_SEL.isChecked() == True:
                self.textBroswerPrintRealTime('123')     
    def PhaseAgain_Findpoint_cb(self):#Phase一阶导数 再次找点
        cmd_text = 'AA 01 F9 AA AA AA'
        action = 'XP/YP Again_Findpoint...'

        #传输 参数
        self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_PhAgainFindPoint, self.print_info_fast, self.Rx_Array, '', self.DoLocking_Flag)
        
        #启动串口子线程
        # self.Uart.start()
        #启动轮询线程, 包含了SendCmd和数据处理
        self.LongTimeCmd_QThread.start()        
             
    def Refresh_HeaterR(self):
        self.RefreshHeaterR_STM32.emit()

    def Call_PowerMeter_cb(self,flag):
        self.Call_PowerMeter.emit(flag)

    def Calibrate_X_IQ_DitherAmp_cb(self):
        #For Calibrate@DitherAmp
        
        self.LockState.setStyleSheet('background-color:yellow') #rgb(0, 255, 00)  
        self.LockPoint_Run.setEnabled(False)  # 灰色
        self.LockPoint_Stop.setEnabled(True)          
        Amp_Array_buf = ''
        #For Calibrate@DitherAmp
        LockCycle_Target = int(self.setting_CDM.value("setup_Calibrate_Locking/Calibrate_Loop_Cycle"))
        
        MZ_Channel_name = 'X_IQ'
        self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_MZ_Channel", 1) #置位，在循环进制中，对应选择回调信号 X_IQ=1
        
        self.DoLocking_Flag = True  
        self.CalibrateLocking_Flag = True
        cmd_text = 'AA 01 F1 01 10 00'
        report_text1 = 'All MZ Loop_Lock Begin...'
        report_text2 = 'Change '+ MZ_Channel_name +' DitherAmp' 
        FileName = ''
        FileName_HeaterR = ''
        #创建数组，接收光功率计的值
        num = int( self.setting_CDM.value("setup_Calibrate_Locking/Calibrate_Loop_Cycle") )
        self.record_Power =['']*num  
        Amp = 0
        
        #需要确保先连接 光功率计
        if self.setting.value("setup_PowerMeter/Flag_Connect_OpticalPower") == False:
            self.textBroswerPrintRealTime('Please Connect PowerMeter')
            self.LockState.setStyleSheet('background-color:gray') #rgb(0, 255, 00)  
            self.LockPoint_Run.setEnabled(True)  # 灰色
            self.LockPoint_Stop.setEnabled(False)   
            self.Calibrate_X_IQ_DitherAmp.setChecked(False)     
        elif self.CalibrateLocking_Flag == True:
            # @MaxMaxMax 
            if self.Lock_MaxMaxMax_EN.isChecked() == True and self.Calibrate_X_IQ_DitherAmp.isChecked() == True:#按最大光功率扫描锁定门限
                Min_DitherAmp = self.setting_CDM.value("setup_Calibrate_Locking/Min_DitherAmp_MaxMaxMax")
                Max_DitherAmp = self.setting_CDM.value("setup_Calibrate_Locking/Max_DitherAmp_MaxMaxMax")                   
                    
                Amp_Step = self.setting_CDM.value("setup_Calibrate_Locking/Step_DitherAmp_MaxMaxMax")                
                Flag_1st = self.setting_CDM.value("setup_Calibrate_Locking/Flag_1st") 
                
                #第一次循环，设置扫描的Amp值
                if Flag_1st == True:
                    
                    report_text = 'For Calibrate@DitherAmp'
                    self.textBroswerPrintRealTime(report_text+' Need LockingLoop num: '+str( (int(Max_DitherAmp) - int(Min_DitherAmp)) ))
                    
                    Amp = int(Min_DitherAmp)
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Current_DitherAmp", Amp) 
                    #第一次启动 校准校准，需要在Min_DitherAmp运行之前，初始化部分参数
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st",False) #置位，防止后续重复进入第一次启动的配置中
                    
                    CDM_SN = self.setting_CDM.value("setup/CDM_SN")
                    self.CDM_T0_Value = self.setting_CDM.value("setup/T0")
                    self.CDM_WL0_Value = round(float(round(float(self.setting_CDM.value("setup/WL0")),1)),1)      
                    folder_path = './log/' + CDM_SN + '/' + CDM_SN +'_'+ str(self.CDM_T0_Value) +'c_'+ str(self.CDM_WL0_Value)+'/' + 'Calibrate_DitherAmp'+ '/'
                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path)
                        # self.textBroswerPrintRealTime("文件夹创建成功")
                    else:
                        # self.textBroswerPrintRealTime("文件夹已存在")
                        None    
                    FileName = folder_path +'RecordPower_For_Calibrate_DitherAmp_MaxMaxMax_'+MZ_Channel_name+'_'+ self.Time_text()+'.csv'        
                    self.setting_CDM.setValue("setup_Calibrate_Locking/FileName",FileName)
                    
                    header_buf = ['1mV','2mV','3mV','4mV','5mV','6mV','7mV','8mV','9mV','10mV','11mV','12mV',\
                                    '13mV','14mV','15mV','16mV','17mV','18mV','19mV','20mV','Avg']
                    Amp_Array_buf =  np.arange(int(Min_DitherAmp), int(Max_DitherAmp),2)
                    
                    header = ['']*(len(Amp_Array_buf)+1)
                    for i in range(len(Amp_Array_buf)):
                            header[i] = header_buf[ int(Amp_Array_buf[i])-1 ]
                    header[len(Amp_Array_buf)] = header_buf[20]
                    # print(header)
                    with open(FileName, 'a', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(header)
                        csvfile.close()                   

                else:#其他 Threshold 的循环中，只需使用同样的参数
                    
                    FileName = self.setting_CDM.value("setup_Calibrate_Locking/FileName")
                    #接收 来自循环进程自动增加Amp_Step步进后的 Amp幅度     
                    Amp = int(float(self.setting_CDM.value("setup_Calibrate_Locking/Current_DitherAmp"))   )   

                if Amp < int(Max_DitherAmp):#确保 到达门限的上限  停止继续循环 
                    #设置Lockthreshold范围:3~12mV,步进1MV，每个步进对应锁定50次且取光功率的平均值作为比较值，该值最小则对应的Lockthreshold为锁定目标
                    #依次为 设置->IQ->Ph->IQ->Ph->IQ->Ph
                    #开始 IQ锁定门限的确认        
                    
                    self.textBroswerPrintRealTime('\nCurrent_'+MZ_Channel_name+'_DitherAmp: '+ str(Amp)+'mV, '+'loop: '+str(Amp - int(Min_DitherAmp)+1) ) 

                    self.XI_LockDither_Set_cb( 1, Amp, self.print_info_no)
                    self.XQ_LockDither_Set_cb( 1, Amp, self.print_info_no)
                    self.XI_LockDither_Rd_cb( self.print_info_no)
                    self.XQ_LockDither_Rd_cb( self.print_info_no)


                    #创建一个数组,分配各个元素的长度
                    array_element_BitNum = ['']*5
                    array_element_BitNum[0] = 1*6#cmd
                    
                    array_element_BitNum[1] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
                    array_element_BitNum[2] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
                    array_element_BitNum[3] = 6*(6+2) #每个元素一次性读取  WordNum*6个字节的长数据+ 一个EXPD_flag、一个EXPD ADC

                    array_element_BitNum[4] = 1*6#所有数据接收完成，'AFAF'
                    
                    self.Uart.Rx_data_WordNum_array.emit(array_element_BitNum)#传递给Uart

                    #传输 参数
                    print_info_buf = ['']*3
                    
                    print_info_buf[0] = 20  #标记数据的个数:1*cmd+6*heaterDA+6*平均导数值+6*实时导数值+1*"AFAF"
                    print_info_buf[1] = self.print_info_no[1]
                    print_info_buf[2] = self.print_info_no[2]
                    
                    self.Refresh_COM_settings(False,'LockPoint')#设置串口响应时间

                    text = report_text1+', '+ report_text2
                    self.textBroswerPrintRealTime(text)                  
            
                    action = text        

                    self.Lock_TimeStart = str(self.Time_text())#记录开始锁定的时间
                    self.textBroswerPrintRealTime('StartTime: '+self.Lock_TimeStart)
                    self.textBroswerPrintRealTime('锁定中.../Doing Locking...')
                            
                    self.LongTimeCmd_QThread.LockCycle_Target = LockCycle_Target
                    self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_XY_Lock, print_info_buf, self.Rx_Array, self.FindPoint_Record_length, 
                                                       self.DoLocking_Flag, FileName, FileName_HeaterR, 
                                                       self.CalibrateLocking_Flag, self.record_Power, float(Amp), float(Amp_Step))
                    #启动轮询线程, 包含了SendCmd和数据处理
                    #锁定50次并记录光功率
                    self.LongTimeCmd_QThread.start()  
                else:
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st", True) 
                    self.textBroswerPrintRealTime('\nCalibrate_'+MZ_Channel_name+'_DitherAmp @MaxMaxMax Done', self.print_info_fast)

                    # #保存 平均值 数据
                    self.record_Avg_Value =[-100]*(int(Max_DitherAmp) - int(Min_DitherAmp)) 
                           
                    #col列*row行的二维数组
                    #对应(Min_DitherAmp,Max_DitherAmp)mV为需要设置的常规列数，再加1列保存前面10列数(所采数的光功率值)各自平均的结果
                    col = ((int(Max_DitherAmp) - int(Min_DitherAmp))/2 +1)
                    row = int(self.setting_CDM.value("setup_Calibrate_Locking/Calibrate_Loop_Cycle")) 
                                
                    self.record_Power =  [[0] * row for _ in range(col)]#二维矩阵                    

                    # 打开CSV文件
                    with open(FileName, mode='r', encoding='utf-8') as csvfile:
                        # 创建csv.reader对象
                        csv_reader = csv.reader(csvfile)
                        # 读取CSV文件的头部
                        header = next(csv_reader)
                        # 逐行读取数据
                        i=0
                        for row in csv_reader:
                            self.record_Power[i] = row # row是一个列表，包含了当前行的所有数据
                            self.record_Avg_Value[i] = self.Calibrate_DitherAmp_Array_Processing(self.record_Power[i])#50次循环锁定的光功率值，取平均值
                            # print(self.record_Power[i],self.record_Avg_Value[i])
                            i = i+1
                        csvfile.close()#关闭文档  
                        
                    # 检查文件是否存在,进行删除，在下一步再进行文档的重新创建和数据的重新保存
                    if os.path.exists(FileName):
                        # 删除文件
                        os.remove(FileName)
                        # print(f"{FileName} has been deleted.")
                    else:
                        # print(f"{FileName} does not exist.") 
                        pass            
                    #将平均值的结果合并进self.record_Power的最后一列
                    for i in range (len(self.record_Avg_Value)):
                        self.record_Power[col-1][i] = self.record_Avg_Value[i]
                            
                    #所有数据存进CSV
                    data = list(zip(*self.record_Power))  # 行列转换
                    # write in DAdata   
                    with open(FileName, 'a', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(header)
                        for i in data:#  write in CSV
                            writer.writerow(i)
                        csvfile.close()    
                    
                    #结束 IQ锁定门限的锁定扫描
                    #开始数据处理
                    index_buf = self.Find_MaxValue_Index(self.record_Avg_Value)
                
                    # Amp_Array_buf =  np.arange(int(Min_DitherAmp), int(Max_DitherAmp), 2)

                    self.XI_LockDither_Set_cb( 1, Amp_Array_buf[index_buf], self.print_info_no)
                    self.XQ_LockDither_Set_cb( 1, Amp_Array_buf[index_buf], self.print_info_no)
                    self.XI_LockDither_Rd_cb(self.print_info_no)
                    self.XQ_LockDither_Rd_cb(self.print_info_no)
                    self.textBroswerPrintRealTime('Set '+MZ_Channel_name+' DitherAmp: '+ str(Amp_Array_buf[index_buf])+'mV '+'Done.\n') 
                    
                    
                    self.LockState.setText('') 
                    self.LockState.setStyleSheet('background-color:gray') 
                    self.LockPoint_Run.setEnabled(True) 
                    self.LockPoint_Stop.setEnabled(False)      
                    self.Calibrate_X_IQ_DitherAmp.setChecked(False)    
            # @MinMinQuad     
            elif self.Lock_MinMinQuad_EN.isChecked() == True and self.Calibrate_X_IQ_DitherAmp.isChecked() == True:   
                Min_DitherAmp = self.setting_CDM.value("setup_Calibrate_Locking/Min_DitherAmp_MinMinQuad")
                Max_DitherAmp = self.setting_CDM.value("setup_Calibrate_Locking/Max_DitherAmp_MinMinQuad")                   
                    
                Amp_Step = self.setting_CDM.value("setup_Calibrate_Locking/Step_DitherAmp_MinMinQuad")                
                Flag_1st = self.setting_CDM.value("setup_Calibrate_Locking/Flag_1st") 
                
                #第一次循环，设置扫描的Amp值
                if Flag_1st == True:
                    
                    report_text = 'For Calibrate@DitherAmp'
                    self.textBroswerPrintRealTime(report_text+' Need LockingLoop num: '+str( (int(Max_DitherAmp) - int(Min_DitherAmp)) ))
                    
                    Amp = int(Min_DitherAmp)
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Current_DitherAmp", Amp) 
                    #第一次启动 校准校准，需要在Min_DitherAmp运行之前，初始化部分参数
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st",False) #置位，防止后续重复进入第一次启动的配置中
                    
                    CDM_SN = self.setting_CDM.value("setup/CDM_SN")
                    self.CDM_T0_Value = self.setting_CDM.value("setup/T0")
                    self.CDM_WL0_Value = round(float(round(float(self.setting_CDM.value("setup/WL0")),1)),1)      
                    folder_path = './log/' + CDM_SN + '/' + CDM_SN +'_'+ str(self.CDM_T0_Value) +'c_'+ str(self.CDM_WL0_Value)+'/' + 'Calibrate_DitherAmp'+ '/'
                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path)
                        # self.textBroswerPrintRealTime("文件夹创建成功")
                    else:
                        # self.textBroswerPrintRealTime("文件夹已存在")
                        None    
                    FileName = folder_path +'RecordPower_For_Calibrate_DitherAmp_MinMinQuad_'+MZ_Channel_name+'_'+ self.Time_text()+'.csv'        
                    self.setting_CDM.setValue("setup_Calibrate_Locking/FileName",FileName)
                    
                    header_buf = ['1mV','2mV','3mV','4mV','5mV','6mV','7mV','8mV','9mV','10mV','11mV','12mV',\
                                    '13mV','14mV','15mV','16mV','17mV','18mV','19mV','20mV','Avg']
                    
                    Amp_Array_buf =  np.arange(int(Min_DitherAmp), int(Max_DitherAmp),2)
                    
                    header = ['']*(len(Amp_Array_buf)+1)
                    for i in range(len(Amp_Array_buf)):
                            header[i] = header_buf[ int(Amp_Array_buf[i])-1 ]
                    header[len(Amp_Array_buf)] = header_buf[20]
                    # print(header)
                    with open(FileName, 'a', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(header)
                        csvfile.close()                   

                else:#其他 Threshold 的循环中，只需使用同样的参数
                    
                    FileName = self.setting_CDM.value("setup_Calibrate_Locking/FileName")
                    #接收 来自循环进程自动增加Amp_Step步进后的 Amp幅度     
                    Amp = int(float(self.setting_CDM.value("setup_Calibrate_Locking/Current_DitherAmp"))   )   

                if Amp < int(Max_DitherAmp):#确保 到达门限的上限  停止继续循环 
                    #设置Lockthreshold范围:3~12mV,步进1MV，每个步进对应锁定50次且取光功率的平均值作为比较值，该值最小则对应的Lockthreshold为锁定目标
                    #依次为 设置->IQ->Ph->IQ->Ph->IQ->Ph
                    #开始 IQ锁定门限的确认        
                    self.textBroswerPrintRealTime('\nCurrent_'+MZ_Channel_name+'_DitherAmp: '+ str(Amp)+'mV, '+'loop: '+str(Amp - int(Min_DitherAmp)+1) ) 

                    self.XI_LockDither_Set_cb( 1, Amp, self.print_info_no)
                    self.XQ_LockDither_Set_cb( 1, Amp, self.print_info_no)
                    self.XI_LockDither_Rd_cb( self.print_info_no)
                    self.XQ_LockDither_Rd_cb( self.print_info_no)

                    #创建一个数组,分配各个元素的长度
                    array_element_BitNum = ['']*5
                    array_element_BitNum[0] = 1*6#cmd
                    
                    array_element_BitNum[1] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
                    array_element_BitNum[2] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
                    array_element_BitNum[3] = 6*(6+2) #每个元素一次性读取  WordNum*6个字节的长数据+ 一个EXPD_flag、一个EXPD ADC

                    array_element_BitNum[4] = 1*6#所有数据接收完成，'AFAF'
                    
                    self.Uart.Rx_data_WordNum_array.emit(array_element_BitNum)#传递给Uart

                    #传输 参数
                    print_info_buf = ['']*3
                    
                    print_info_buf[0] = 20  #标记数据的个数:1*cmd+6*heaterDA+6*平均导数值+6*实时导数值+1*"AFAF"
                    print_info_buf[1] = self.print_info_no[1]
                    print_info_buf[2] = self.print_info_no[2]
                    
                    self.Refresh_COM_settings(False,'LockPoint')#设置串口响应时间

                    text = report_text1+', '+ report_text2
                    self.textBroswerPrintRealTime(text)                  
            
                    action = text        

                    self.Lock_TimeStart = str(self.Time_text())#记录开始锁定的时间
                    self.textBroswerPrintRealTime('StartTime: '+self.Lock_TimeStart)
                    self.textBroswerPrintRealTime('锁定中...')
                            
                    self.LongTimeCmd_QThread.LockCycle_Target = LockCycle_Target
                    self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_XY_Lock, print_info_buf, self.Rx_Array, self.FindPoint_Record_length, 
                                                       self.DoLocking_Flag, FileName, FileName_HeaterR, 
                                                       self.CalibrateLocking_Flag, self.record_Power, float(Amp), float(Amp_Step))
                    #启动轮询线程, 包含了SendCmd和数据处理
                    #锁定50次并记录光功率
                    self.LongTimeCmd_QThread.start()  
                else:
                    
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st", True) 
                    self.textBroswerPrintRealTime('\nCalibrate_'+MZ_Channel_name+'_DitherAmp @Find_MinValue_Index Done', self.print_info_fast)

                    # #保存 平均值 数据
                    self.record_Avg_Value =[-100]*(int(Max_DitherAmp) - int(Min_DitherAmp)) 
                           
                    #col列*row行的二维数组
                    #对应(Min_DitherAmp,Max_DitherAmp)mV为需要设置的常规列数，再加1列保存前面10列数(所采数的光功率值)各自平均的结果
                    col = (int(Max_DitherAmp) - int(Min_DitherAmp) +1)
                    row = int(self.setting_CDM.value("setup_Calibrate_Locking/Calibrate_Loop_Cycle")) 
                                
                    self.record_Power =  [[0] * row for _ in range(col)]#二维矩阵                    

                    # 打开CSV文件
                    with open(FileName, mode='r', encoding='utf-8') as csvfile:
                        # 创建csv.reader对象
                        csv_reader = csv.reader(csvfile)
                        # 读取CSV文件的头部
                        header = next(csv_reader)
                        # 逐行读取数据
                        i=0
                        for row in csv_reader:
                            self.record_Power[i] = row # row是一个列表，包含了当前行的所有数据
                            self.record_Avg_Value[i] = self.Calibrate_DitherAmp_Array_Processing(self.record_Power[i])#50次循环锁定的光功率值，取平均值
                            # print(self.record_Power[i],self.record_Avg_Value[i])
                            i = i+1
                        csvfile.close()#关闭文档  
                        
                    # 检查文件是否存在,进行删除，在下一步再进行文档的重新创建和数据的重新保存
                    if os.path.exists(FileName):
                        # 删除文件
                        os.remove(FileName)
                        # print(f"{FileName} has been deleted.")
                    else:
                        # print(f"{FileName} does not exist.") 
                        pass            
                    sleep(0.1)
                        
                    #将平均值的结果合并进self.record_Power的最后一列
                    for i in range (len(self.record_Avg_Value)):
                        self.record_Power[col-1][i] = self.record_Avg_Value[i]
                            
                    #所有数据存进CSV
                    data = list(zip(*self.record_Power))  # 行列转换
                    # write in DAdata   
                    with open(FileName, 'a', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(header)
                        for i in data:#  write in CSV
                            writer.writerow(i)
                        csvfile.close()    
                    
                    #结束 IQ锁定门限的锁定扫描
                    #开始数据处理
                    index_buf = self.Find_MinValue_Index(self.record_Avg_Value)
                
                    # Amp_Array_buf =  np.arange(int(Min_DitherAmp), int(Max_DitherAmp))

                    self.XI_LockDither_Set_cb( 1, Amp_Array_buf[index_buf], self.print_info_no)
                    self.XQ_LockDither_Set_cb( 1, Amp_Array_buf[index_buf], self.print_info_no)
                    self.XI_LockDither_Rd_cb(self.print_info_no)
                    self.XQ_LockDither_Rd_cb(self.print_info_no)
                    self.textBroswerPrintRealTime('Set '+MZ_Channel_name+' DitherAmp: '+ str(Amp_Array_buf[index_buf])+'mV '+'Done.\n') 

                    self.LockState.setText('') 
                    self.LockState.setStyleSheet('background-color:gray') 
                    self.LockPoint_Run.setEnabled(True) 
                    self.LockPoint_Stop.setEnabled(False)      
                    self.Calibrate_X_IQ_DitherAmp.setChecked(False)
                                        
            else:
                self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st", True) 
                self.LockState.setText('') 
                self.LockState.setStyleSheet('background-color:gray')  
                self.LockPoint_Run.setEnabled(True) 
                self.LockPoint_Stop.setEnabled(False)
                self.Calibrate_X_IQ_DitherAmp.setChecked(False)    
    
    def Calibrate_Y_IQ_DitherAmp_cb(self):
        #For Calibrate@DitherAmp
        
        self.LockState.setStyleSheet('background-color:yellow') #rgb(0, 255, 00)  
        self.LockPoint_Run.setEnabled(False)  # 灰色
        self.LockPoint_Stop.setEnabled(True)           

        #For Calibrate@DitherAmp
        LockCycle_Target = int(self.setting_CDM.value("setup_Calibrate_Locking/Calibrate_Loop_Cycle"))
        Amp_Array_buf = ''
        #修改
        MZ_Channel_name = 'Y_IQ'
        self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_MZ_Channel", 2) #置位，在循环进制中，对应选择回调信号 Y_IQ=2
        
        self.DoLocking_Flag = True  
        self.CalibrateLocking_Flag = True
        cmd_text = 'AA 01 F1 01 10 00'
        report_text1 = 'All MZ Loop_Lock Begin...'
        report_text2 = 'Change '+ MZ_Channel_name +' DitherAmp' 
        FileName = ''
        FileName_HeaterR = ''
        #创建数组，接收光功率计的值
        num = int( self.setting_CDM.value("setup_Calibrate_Locking/Calibrate_Loop_Cycle") )
        self.record_Power =['']*num  
        Amp = 0
        
        #需要确保先连接 光功率计
        if self.setting.value("setup_PowerMeter/Flag_Connect_OpticalPower") == False:
            self.textBroswerPrintRealTime('Please Connect PowerMeter')
            self.LockState.setStyleSheet('background-color:gray') #rgb(0, 255, 00)  
            self.LockPoint_Run.setEnabled(True)  # 灰色
            self.LockPoint_Stop.setEnabled(False)      
            self.Calibrate_Y_IQ_DitherAmp.setChecked(False) #修改    
        elif self.CalibrateLocking_Flag == True:
            # @MaxMaxMax #按最大光功率扫描锁定门限
            if self.Lock_MaxMaxMax_EN.isChecked() == True and self.Calibrate_Y_IQ_DitherAmp.isChecked() == True:#修改

                Min_DitherAmp = self.setting_CDM.value("setup_Calibrate_Locking/Min_DitherAmp_MaxMaxMax")
                Max_DitherAmp = self.setting_CDM.value("setup_Calibrate_Locking/Max_DitherAmp_MaxMaxMax")                   
                    
                Amp_Step = self.setting_CDM.value("setup_Calibrate_Locking/Step_DitherAmp_MaxMaxMax")                
                Flag_1st = self.setting_CDM.value("setup_Calibrate_Locking/Flag_1st") 
                
                #第一次循环，设置扫描的Amp
                if Flag_1st == True:
                    
                    report_text = 'For Calibrate@DitherAmp'
                    self.textBroswerPrintRealTime(report_text+' Need LockingLoop num: '+str( (int(Max_DitherAmp) - int(Min_DitherAmp)) ))
                    
                    Amp = int(Min_DitherAmp)
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Current_DitherAmp", Amp) 
                    #第一次启动 校准校准，需要在Min_DitherAmp运行之前，初始化部分参数
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st",False) #置位，防止后续重复进入第一次启动的配置中
                    
                    CDM_SN = self.setting_CDM.value("setup/CDM_SN")
                    self.CDM_T0_Value = self.setting_CDM.value("setup/T0")
                    self.CDM_WL0_Value = round(float(round(float(self.setting_CDM.value("setup/WL0")),1)),1)      
                    folder_path = './log/' + CDM_SN + '/' + CDM_SN +'_'+ str(self.CDM_T0_Value) +'c_'+ str(self.CDM_WL0_Value)+'/' + 'Calibrate_DitherAmp'+ '/'
                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path)
                        # self.textBroswerPrintRealTime("文件夹创建成功")
                    else:
                        # self.textBroswerPrintRealTime("文件夹已存在")
                        None    
                    FileName = folder_path +'RecordPower_For_Calibrate_DitherAmp_MaxMaxMax_'+MZ_Channel_name+'_'+ self.Time_text()+'.csv'        
                    self.setting_CDM.setValue("setup_Calibrate_Locking/FileName",FileName)
                    
                    header_buf = ['1mV','2mV','3mV','4mV','5mV','6mV','7mV','8mV','9mV','10mV','11mV','12mV',\
                                    '13mV','14mV','15mV','16mV','17mV','18mV','19mV','20mV','Avg']
                    
                    Amp_Array_buf =  np.arange(int(Min_DitherAmp), int(Max_DitherAmp),2)
                    
                    header = ['']*(len(Amp_Array_buf)+1)
                    for i in range(len(Amp_Array_buf)):
                            header[i] = header_buf[ int(Amp_Array_buf[i])-1 ]
                    header[len(Amp_Array_buf)] = header_buf[20]
                    # print(header)
                    with open(FileName, 'a', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(header)
                        csvfile.close()                   

                else:#其他 Threshold 的循环中，只需使用同样的参数
                    
                    FileName = self.setting_CDM.value("setup_Calibrate_Locking/FileName")
                    #接收 来自循环进程自动增加Amp_Step步进后的 Amp幅度     
                    Amp = int(float(self.setting_CDM.value("setup_Calibrate_Locking/Current_DitherAmp"))   )   

                if Amp < int(Max_DitherAmp):#确保 到达门限的上限  停止继续循环 
                    #设置Lockthreshold范围:3~12mV,步进1MV，每个步进对应锁定50次且取光功率的平均值作为比较值，该值最小则对应的Lockthreshold为锁定目标
                    #依次为 设置->IQ->Ph->IQ->Ph->IQ->Ph
                    #开始 IQ锁定门限的确认        
                    
                    self.textBroswerPrintRealTime('\nCurrent_'+MZ_Channel_name+'_DitherAmp: '+ str(Amp)+'mV, '+'loop: '+str(Amp - int(Min_DitherAmp)+1) ) 
   
                    self.YI_LockDither_Set_cb( 1, Amp, self.print_info_no)#修改
                    self.YQ_LockDither_Set_cb( 1, Amp, self.print_info_no)#修改
                    self.YI_LockDither_Rd_cb( self.print_info_no)#修改
                    self.YQ_LockDither_Rd_cb( self.print_info_no)#修改


                    #创建一个数组,分配各个元素的长度
                    array_element_BitNum = ['']*5
                    array_element_BitNum[0] = 1*6#cmd
                    
                    array_element_BitNum[1] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
                    array_element_BitNum[2] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
                    array_element_BitNum[3] = 6*(6+2) #每个元素一次性读取  WordNum*6个字节的长数据+ 一个EXPD_flag、一个EXPD ADC

                    array_element_BitNum[4] = 1*6#所有数据接收完成，'AFAF'
                    
                    self.Uart.Rx_data_WordNum_array.emit(array_element_BitNum)#传递给Uart

                    #传输 参数
                    print_info_buf = ['']*3
                    
                    print_info_buf[0] = 20  #标记数据的个数:1*cmd+6*heaterDA+6*平均导数值+6*实时导数值+1*"AFAF"
                    print_info_buf[1] = self.print_info_no[1]
                    print_info_buf[2] = self.print_info_no[2]
                    
                    self.Refresh_COM_settings(False,'LockPoint')#设置串口响应时间

                    text = report_text1+', '+ report_text2
                    self.textBroswerPrintRealTime(text)                  
            
                    action = text        

                    self.Lock_TimeStart = str(self.Time_text())#记录开始锁定的时间
                    self.textBroswerPrintRealTime('StartTime: '+self.Lock_TimeStart)
                    self.textBroswerPrintRealTime('锁定中.../Doing Locking...')
                            
                    self.LongTimeCmd_QThread.LockCycle_Target = LockCycle_Target
                    self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_XY_Lock, print_info_buf, self.Rx_Array, self.FindPoint_Record_length, 
                                                       self.DoLocking_Flag, FileName, FileName_HeaterR, 
                                                       self.CalibrateLocking_Flag, self.record_Power, float(Amp), float(Amp_Step))
                    #启动轮询线程, 包含了SendCmd和数据处理
                    #锁定50次并记录光功率
                    self.LongTimeCmd_QThread.start()  
                else:
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st", True) 
                    self.textBroswerPrintRealTime('\nCalibrate_'+MZ_Channel_name+'_DitherAmp @MaxMaxMax Done', self.print_info_fast)

                    # #保存 平均值 数据
                    self.record_Avg_Value =[-100]*(int(Max_DitherAmp) - int(Min_DitherAmp)) 
                           
                    #col列*row行的二维数组
                    #对应(Min_DitherAmp,Max_DitherAmp)mV为需要设置的常规列数，再加1列保存前面10列数(所采数的光功率值)各自平均的结果
                    col = (int(Max_DitherAmp) - int(Min_DitherAmp) +1)
                    row = int(self.setting_CDM.value("setup_Calibrate_Locking/Calibrate_Loop_Cycle")) 
                                
                    self.record_Power =  [[0] * row for _ in range(col)]#二维矩阵                    

                    # 打开CSV文件
                    with open(FileName, mode='r', encoding='utf-8') as csvfile:
                        # 创建csv.reader对象
                        csv_reader = csv.reader(csvfile)
                        # 读取CSV文件的头部
                        header = next(csv_reader)
                        # 逐行读取数据
                        i=0
                        for row in csv_reader:
                            self.record_Power[i] = row # row是一个列表，包含了当前行的所有数据
                            self.record_Avg_Value[i] = self.Calibrate_DitherAmp_Array_Processing(self.record_Power[i])#50次循环锁定的光功率值，取平均值
                            # print(self.record_Power[i],self.record_Avg_Value[i])
                            i = i+1
                        csvfile.close()#关闭文档  
                        
                    # 检查文件是否存在,进行删除，在下一步再进行文档的重新创建和数据的重新保存
                    if os.path.exists(FileName):
                        # 删除文件
                        os.remove(FileName)
                        # print(f"{FileName} has been deleted.")
                    else:
                        # print(f"{FileName} does not exist.") 
                        pass            
                    sleep(0.1)
                        
                    #将平均值的结果合并进self.record_Power的最后一列
                    for i in range (len(self.record_Avg_Value)):
                        self.record_Power[col-1][i] = self.record_Avg_Value[i]
                            
                    #所有数据存进CSV
                    data = list(zip(*self.record_Power))  # 行列转换
                    # write in DAdata   
                    with open(FileName, 'a', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(header)
                        for i in data:#  write in CSV
                            writer.writerow(i)
                        csvfile.close()    
                    
                    #结束 IQ锁定门限的锁定扫描
                    #开始数据处理
                    index_buf = self.Find_MaxValue_Index(self.record_Avg_Value)
                
                    # Amp_Array_buf =  np.arange(int(Min_DitherAmp), int(Max_DitherAmp))

                    self.YI_LockDither_Set_cb( 1, Amp_Array_buf[index_buf], self.print_info_no)#修改
                    self.YQ_LockDither_Set_cb( 1, Amp_Array_buf[index_buf], self.print_info_no)#修改
                    self.YI_LockDither_Rd_cb(self.print_info_no)#修改
                    self.YQ_LockDither_Rd_cb(self.print_info_no)#修改                   
                    
                    self.textBroswerPrintRealTime('Set '+MZ_Channel_name+' DitherAmp: '+ str(Amp_Array_buf[index_buf])+'mV '+'Done.\n') 

                    self.LockState.setText('') 
                    self.LockState.setStyleSheet('background-color:gray')
                    self.LockPoint_Run.setEnabled(True) 
                    self.LockPoint_Stop.setEnabled(False)    
                    self.Calibrate_Y_IQ_DitherAmp.setChecked(False)#修改   
                    
            elif self.Lock_MinMinQuad_EN.isChecked() == True and self.Calibrate_Y_IQ_DitherAmp.isChecked() == True:   
                Min_DitherAmp = self.setting_CDM.value("setup_Calibrate_Locking/Min_DitherAmp_MinMinQuad")
                Max_DitherAmp = self.setting_CDM.value("setup_Calibrate_Locking/Max_DitherAmp_MinMinQuad")                   
                    
                Amp_Step = self.setting_CDM.value("setup_Calibrate_Locking/Step_DitherAmp_MinMinQuad")                
                Flag_1st = self.setting_CDM.value("setup_Calibrate_Locking/Flag_1st") 
                
                #第一次循环，设置扫描的Amp值
                if Flag_1st == True:
                    
                    report_text = 'For Calibrate@DitherAmp'
                    self.textBroswerPrintRealTime(report_text+' Need LockingLoop num: '+str( (int(Max_DitherAmp) - int(Min_DitherAmp)) ))
                    
                    Amp = int(Min_DitherAmp)
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Current_DitherAmp", Amp) 
                    #第一次启动 校准校准，需要在Min_DitherAmp运行之前，初始化部分参数
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st",False) #置位，防止后续重复进入第一次启动的配置中
                    
                    CDM_SN = self.setting_CDM.value("setup/CDM_SN")
                    self.CDM_T0_Value = self.setting_CDM.value("setup/T0")
                    self.CDM_WL0_Value = round(float(round(float(self.setting_CDM.value("setup/WL0")),1)),1)      
                    folder_path = './log/' + CDM_SN + '/' + CDM_SN +'_'+ str(self.CDM_T0_Value) +'c_'+ str(self.CDM_WL0_Value)+'/' + 'Calibrate_DitherAmp'+ '/'
                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path)
                        # self.textBroswerPrintRealTime("文件夹创建成功")
                    else:
                        # self.textBroswerPrintRealTime("文件夹已存在")
                        None    
                    FileName = folder_path +'RecordPower_For_Calibrate_DitherAmp_MinMinQuad_'+MZ_Channel_name+'_'+ self.Time_text()+'.csv'        
                    self.setting_CDM.setValue("setup_Calibrate_Locking/FileName",FileName)
                    
                    header_buf = ['1mV','2mV','3mV','4mV','5mV','6mV','7mV','8mV','9mV','10mV','11mV','12mV',\
                                    '13mV','14mV','15mV','16mV','17mV','18mV','19mV','20mV','Avg']
                    
                    Amp_Array_buf =  np.arange(int(Min_DitherAmp), int(Max_DitherAmp),2)
                    
                    header = ['']*(len(Amp_Array_buf)+1)
                    for i in range(len(Amp_Array_buf)):
                            header[i] = header_buf[ int(Amp_Array_buf[i])-1 ]
                    header[len(Amp_Array_buf)] = header_buf[20]
                    # print(header)
                    with open(FileName, 'a', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(header)
                        csvfile.close()                   

                else:#其他 Threshold 的循环中，只需使用同样的参数
                    FileName = self.setting_CDM.value("setup_Calibrate_Locking/FileName")
                    #接收 来自循环进程自动增加Amp_Step步进后的 Amp幅度     
                    Amp = int(float(self.setting_CDM.value("setup_Calibrate_Locking/Current_DitherAmp"))   )   
                    
                if Amp < int(Max_DitherAmp):#确保 到达门限的上限  停止继续循环 
                    #设置Lockthreshold范围:3~12mV,步进1MV，每个步进对应锁定50次且取光功率的平均值作为比较值，该值最小则对应的Lockthreshold为锁定目标
                    #依次为 设置->IQ->Ph->IQ->Ph->IQ->Ph
                    #开始 IQ锁定门限的确认        
                    
                    self.textBroswerPrintRealTime('\nCurrent_'+MZ_Channel_name+'_DitherAmp: '+ str(Amp)+'mV, '+'loop: '+str(Amp - int(Min_DitherAmp)+1) ) 
                    self.YI_LockDither_Set_cb( 1, Amp, self.print_info_no)
                    self.YQ_LockDither_Set_cb( 1, Amp, self.print_info_no)
                    self.YI_LockDither_Rd_cb( self.print_info_no)
                    self.YQ_LockDither_Rd_cb( self.print_info_no)


                    #创建一个数组,分配各个元素的长度
                    array_element_BitNum = ['']*5
                    array_element_BitNum[0] = 1*6#cmd
                    
                    array_element_BitNum[1] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
                    array_element_BitNum[2] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
                    array_element_BitNum[3] = 6*(6+2) #每个元素一次性读取  WordNum*6个字节的长数据+ 一个EXPD_flag、一个EXPD ADC

                    array_element_BitNum[4] = 1*6#所有数据接收完成，'AFAF'
                    
                    self.Uart.Rx_data_WordNum_array.emit(array_element_BitNum)#传递给Uart

                    #传输 参数
                    print_info_buf = ['']*3
                    
                    print_info_buf[0] = 20  #标记数据的个数:1*cmd+6*heaterDA+6*平均导数值+6*实时导数值+1*"AFAF"
                    print_info_buf[1] = self.print_info_no[1]
                    print_info_buf[2] = self.print_info_no[2]
                    
                    self.Refresh_COM_settings(False,'LockPoint')#设置串口响应时间

                    text = report_text1+', '+ report_text2
                    self.textBroswerPrintRealTime(text)                  
            
                    action = text        

                    self.Lock_TimeStart = str(self.Time_text())#记录开始锁定的时间
                    self.textBroswerPrintRealTime('StartTime: '+self.Lock_TimeStart)
                    self.textBroswerPrintRealTime('锁定中.../Doing Locking...')
                            
                    self.LongTimeCmd_QThread.LockCycle_Target = LockCycle_Target
                    self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_XY_Lock, print_info_buf, self.Rx_Array, self.FindPoint_Record_length, 
                                                       self.DoLocking_Flag, FileName, FileName_HeaterR, 
                                                       self.CalibrateLocking_Flag, self.record_Power, float(Amp), float(Amp_Step))
                    #启动轮询线程, 包含了SendCmd和数据处理
                    #锁定50次并记录光功率
                    self.LongTimeCmd_QThread.start()  
                else:
                    
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st", True) 
                    self.textBroswerPrintRealTime('\nCalibrate_'+MZ_Channel_name+'_DitherAmp @MinMinQuad Done', self.print_info_fast)

                    # #保存 平均值 数据
                    self.record_Avg_Value =[-100]*(int(Max_DitherAmp) - int(Min_DitherAmp)) 
                           
                    #col列*row行的二维数组
                    #对应(Min_DitherAmp,Max_DitherAmp)mV为需要设置的常规列数，再加1列保存前面10列数(所采数的光功率值)各自平均的结果
                    col = (int(Max_DitherAmp) - int(Min_DitherAmp) +1)
                    row = int(self.setting_CDM.value("setup_Calibrate_Locking/Calibrate_Loop_Cycle")) 
                                
                    self.record_Power =  [[0] * row for _ in range(col)]#二维矩阵                    

                    # 打开CSV文件
                    with open(FileName, mode='r', encoding='utf-8') as csvfile:
                        # 创建csv.reader对象
                        csv_reader = csv.reader(csvfile)
                        # 读取CSV文件的头部
                        header = next(csv_reader)
                        # 逐行读取数据
                        i=0
                        for row in csv_reader:
                            self.record_Power[i] = row # row是一个列表，包含了当前行的所有数据
                            self.record_Avg_Value[i] = self.Calibrate_DitherAmp_Array_Processing(self.record_Power[i])#50次循环锁定的光功率值，取平均值
                            # print(self.record_Power[i],self.record_Avg_Value[i])
                            i = i+1
                        csvfile.close()#关闭文档  
                        
                    # 检查文件是否存在,进行删除，在下一步再进行文档的重新创建和数据的重新保存
                    if os.path.exists(FileName):
                        # 删除文件
                        os.remove(FileName)
                        # print(f"{FileName} has been deleted.")
                    else:
                        # print(f"{FileName} does not exist.") 
                        pass            

                        
                    #将平均值的结果合并进self.record_Power的最后一列
                    for i in range (len(self.record_Avg_Value)):
                        self.record_Power[col-1][i] = self.record_Avg_Value[i]
                            
                    #所有数据存进CSV
                    data = list(zip(*self.record_Power))  # 行列转换
                    # write in DAdata   
                    with open(FileName, 'a', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(header)
                        for i in data:#  write in CSV
                            writer.writerow(i)
                        csvfile.close()    
                    
                    #结束 IQ锁定门限的锁定扫描
                    #开始数据处理
                    index_buf = self.Find_MinValue_Index(self.record_Avg_Value)
                    # Amp_Array_buf =  np.arange(int(Min_DitherAmp), int(Max_DitherAmp))

                    self.YI_LockDither_Set_cb( 1, Amp_Array_buf[index_buf], self.print_info_no)
                    self.YQ_LockDither_Set_cb( 1, Amp_Array_buf[index_buf], self.print_info_no)
                    self.YI_LockDither_Rd_cb(self.print_info_no)
                    self.YQ_LockDither_Rd_cb(self.print_info_no)
                    self.textBroswerPrintRealTime('Set '+MZ_Channel_name+' DitherAmp: '+ str(Amp_Array_buf[index_buf])+'mV '+'Done.\n') 
                    self.LockState.setText('') 
                    self.LockState.setStyleSheet('background-color:gray') 
                    self.LockPoint_Run.setEnabled(True) 
                    self.LockPoint_Stop.setEnabled(False)    
                    self.Calibrate_Y_IQ_DitherAmp.setChecked(False)
            else:
                self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st", True) 
                self.LockState.setText('') 
                self.LockState.setStyleSheet('background-color:gray')  
                self.LockPoint_Run.setEnabled(True) 
                self.LockPoint_Stop.setEnabled(False)  
                self.Calibrate_Y_IQ_DitherAmp.setChecked(False) 
                
    def Calibrate_XP_DitherAmp_cb(self):
        #For Calibrate@DitherAmp
        self.LockState.setStyleSheet('background-color:yellow') #rgb(0, 255, 00)  
        self.LockPoint_Run.setEnabled(False)  # 灰色
        self.LockPoint_Stop.setEnabled(True)         

        #For Calibrate@DitherAmp
        LockCycle_Target = int(self.setting_CDM.value("setup_Calibrate_Locking/Calibrate_Loop_Cycle"))
        Amp_Array_buf = ''
        #修改
        MZ_Channel_name = 'XP'
        self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_MZ_Channel", 3) #置位，在循环进制中，对应选择回调信号 XP=3
        
        self.DoLocking_Flag = True  
        self.CalibrateLocking_Flag = True
        cmd_text = 'AA 01 F1 01 10 00'
        report_text1 = 'All MZ Loop_Lock Begin... '
        report_text2 = 'Change '+ MZ_Channel_name +' DitherAmp' 
        FileName = ''
        FileName_HeaterR = ''
        #创建数组，接收光功率计的值
        num = int( self.setting_CDM.value("setup_Calibrate_Locking/Calibrate_Loop_Cycle") )
        self.record_Power =['']*num  
        Amp = 0
        #需要确保先连接 光功率计
        if self.setting.value("setup_PowerMeter/Flag_Connect_OpticalPower") == False:
            self.textBroswerPrintRealTime('Please Connect PowerMeter')
            self.LockState.setStyleSheet('background-color:gray') #rgb(0, 255, 00)  
            self.LockPoint_Run.setEnabled(True)  # 灰色
            self.LockPoint_Stop.setEnabled(False)   
            self.Calibrate_XP_DitherAmp.setChecked(False) #修改               
        elif self.CalibrateLocking_Flag == True:
            # @MaxMaxMax #按最大光功率扫描锁定门限
            if self.Lock_MaxMaxMax_EN.isChecked() == True and self.Calibrate_XP_DitherAmp.isChecked() == True:#修改

                Min_DitherAmp = self.setting_CDM.value("setup_Calibrate_Locking/Min_DitherAmp_MaxMaxMax")
                Max_DitherAmp = self.setting_CDM.value("setup_Calibrate_Locking/Max_DitherAmp_MaxMaxMax")                   
                    
                Amp_Step = self.setting_CDM.value("setup_Calibrate_Locking/Step_DitherAmp_MaxMaxMax")                
                Flag_1st = self.setting_CDM.value("setup_Calibrate_Locking/Flag_1st") 
                #第一次循环，设置扫描的Amp值
                if Flag_1st == True:
                    
                    report_text = 'For Calibrate@DitherAmp'
                    self.textBroswerPrintRealTime(report_text+' Need LockingLoop num: '+str( (int(Max_DitherAmp) - int(Min_DitherAmp)) ))
                    
                    Amp = int(Min_DitherAmp)
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Current_DitherAmp", Amp) 
                    #第一次启动 校准校准，需要在Min_DitherAmp运行之前，初始化部分参数
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st",False) #置位，防止后续重复进入第一次启动的配置中
                    
                    CDM_SN = self.setting_CDM.value("setup/CDM_SN")
                    self.CDM_T0_Value = self.setting_CDM.value("setup/T0")
                    self.CDM_WL0_Value = round(float(round(float(self.setting_CDM.value("setup/WL0")),1)),1)      
                    folder_path = './log/' + CDM_SN + '/' + CDM_SN +'_'+ str(self.CDM_T0_Value) +'c_'+ str(self.CDM_WL0_Value)+'/' + 'Calibrate_DitherAmp'+ '/'
                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path)
                        # self.textBroswerPrintRealTime("文件夹创建成功")
                    else:
                        # self.textBroswerPrintRealTime("文件夹已存在")
                        None    
                    FileName = folder_path +'RecordPower_For_Calibrate_DitherAmp_MaxMaxMax_'+MZ_Channel_name+'_'+ self.Time_text()+'.csv'        
                    self.setting_CDM.setValue("setup_Calibrate_Locking/FileName",FileName)
                    
                    header_buf = ['1mV','2mV','3mV','4mV','5mV','6mV','7mV','8mV','9mV','10mV','11mV','12mV',\
                                    '13mV','14mV','15mV','16mV','17mV','18mV','19mV','20mV','Avg']
                    
                    Amp_Array_buf =  np.arange(int(Min_DitherAmp), int(Max_DitherAmp),2)
                    
                    header = ['']*(len(Amp_Array_buf)+1)
                    for i in range(len(Amp_Array_buf)):
                            header[i] = header_buf[ int(Amp_Array_buf[i])-1 ]
                    header[len(Amp_Array_buf)] = header_buf[20]
                    # print(header)
                    with open(FileName, 'a', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(header)
                        csvfile.close()                   

                else:#其他 Threshold 的循环中，只需使用同样的参数
                    
                    FileName = self.setting_CDM.value("setup_Calibrate_Locking/FileName")
                    #接收 来自循环进程自动增加Amp_Step步进后的 Amp幅度     
                    Amp = int(float(self.setting_CDM.value("setup_Calibrate_Locking/Current_DitherAmp"))   )   

                if Amp < int(Max_DitherAmp):#确保 到达门限的上限  停止继续循环 
                    #设置Lockthreshold范围:3~12mV,步进1MV，每个步进对应锁定50次且取光功率的平均值作为比较值，该值最小则对应的Lockthreshold为锁定目标
                    #依次为 设置->IQ->Ph->IQ->Ph->IQ->Ph
                    #开始 IQ锁定门限的确认        
                    self.textBroswerPrintRealTime('\nCurrent_'+MZ_Channel_name+'_DitherAmp: '+ str(Amp)+'mV, '+'loop: '+str(Amp - int(Min_DitherAmp)+1)) 
                    
                    self.XP_LockDither_Set_cb( 1, Amp, Amp, self.print_info_no)#修改
                    self.XP_LockDither_Rd_cb( self.print_info_no)#修改

                    #创建一个数组,分配各个元素的长度
                    array_element_BitNum = ['']*5
                    array_element_BitNum[0] = 1*6#cmd
                    
                    array_element_BitNum[1] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
                    array_element_BitNum[2] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
                    array_element_BitNum[3] = 6*(6+2) #每个元素一次性读取  WordNum*6个字节的长数据+ 一个EXPD_flag、一个EXPD ADC

                    array_element_BitNum[4] = 1*6#所有数据接收完成，'AFAF'
                    
                    self.Uart.Rx_data_WordNum_array.emit(array_element_BitNum)#传递给Uart

                    #传输 参数
                    print_info_buf = ['']*3
                    
                    print_info_buf[0] = 20  #标记数据的个数:1*cmd+6*heaterDA+6*平均导数值+6*实时导数值+1*"AFAF"
                    print_info_buf[1] = self.print_info_no[1]
                    print_info_buf[2] = self.print_info_no[2]
                    
                    self.Refresh_COM_settings(False,'LockPoint')#设置串口响应时间

                    text = report_text1+', '+ report_text2
                    self.textBroswerPrintRealTime(text)                  
            
                    action = text        

                    self.Lock_TimeStart = str(self.Time_text())#记录开始锁定的时间
                    self.textBroswerPrintRealTime('StartTime: '+self.Lock_TimeStart)
                    self.textBroswerPrintRealTime('锁定中...')
                            
                    self.LongTimeCmd_QThread.LockCycle_Target = LockCycle_Target
                    self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_XY_Lock, print_info_buf, self.Rx_Array, self.FindPoint_Record_length, 
                                                       self.DoLocking_Flag, FileName, FileName_HeaterR, 
                                                       self.CalibrateLocking_Flag, self.record_Power, float(Amp), float(Amp_Step))
                    #启动轮询线程, 包含了SendCmd和数据处理
                    #锁定50次并记录光功率
                    self.LongTimeCmd_QThread.start()  
                else:
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st", True) 
                    self.textBroswerPrintRealTime('\nCalibrate_'+MZ_Channel_name+'_DitherAmp @MaxMaxMax Done', self.print_info_fast)

                    # #保存 平均值 数据
                    self.record_Avg_Value =[-100]*(int(Max_DitherAmp) - int(Min_DitherAmp)) 
                           
                    #col列*row行的二维数组
                    #对应(Min_DitherAmp,Max_DitherAmp)mV为需要设置的常规列数，再加1列保存前面10列数(所采数的光功率值)各自平均的结果
                    col = (int(Max_DitherAmp) - int(Min_DitherAmp) +1)
                    row = int(self.setting_CDM.value("setup_Calibrate_Locking/Calibrate_Loop_Cycle")) 
                                
                    self.record_Power =  [[0] * row for _ in range(col)]#二维矩阵                    

                    # 打开CSV文件
                    with open(FileName, mode='r', encoding='utf-8') as csvfile:
                        # 创建csv.reader对象
                        csv_reader = csv.reader(csvfile)
                        # 读取CSV文件的头部
                        header = next(csv_reader)
                        # 逐行读取数据
                        i=0
                        for row in csv_reader:
                            self.record_Power[i] = row # row是一个列表，包含了当前行的所有数据
                            self.record_Avg_Value[i] = self.Calibrate_DitherAmp_Array_Processing(self.record_Power[i])#50次循环锁定的光功率值，取平均值
                            # print(self.record_Power[i],self.record_Avg_Value[i])
                            i = i+1
                        csvfile.close()#关闭文档  
                        
                    # 检查文件是否存在,进行删除，在下一步再进行文档的重新创建和数据的重新保存
                    if os.path.exists(FileName):
                        # 删除文件
                        os.remove(FileName)
                        # print(f"{FileName} has been deleted.")
                    else:
                        # print(f"{FileName} does not exist.") 
                        pass            
                        
                    #将平均值的结果合并进self.record_Power的最后一列
                    for i in range (len(self.record_Avg_Value)):
                        self.record_Power[col-1][i] = self.record_Avg_Value[i]
                            
                    #所有数据存进CSV
                    data = list(zip(*self.record_Power))  # 行列转换
                    # write in DAdata   
                    with open(FileName, 'a', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(header)
                        for i in data:#  write in CSV
                            writer.writerow(i)
                        csvfile.close()    
                    
                    #结束 IQ锁定门限的锁定扫描
                    #开始数据处理
                    index_buf = self.Find_MaxValue_Index(self.record_Avg_Value)
                
                    # Amp_Array_buf =  np.arange(int(Min_DitherAmp), int(Max_DitherAmp))

                    self.XP_LockDither_Set_cb( 1, Amp_Array_buf[index_buf], Amp_Array_buf[index_buf], self.print_info_no)#修改
                    self.XP_LockDither_Rd_cb( self.print_info_no)#修改      
                    
                    self.textBroswerPrintRealTime('Set '+MZ_Channel_name+' DitherAmp: '+ str(Amp_Array_buf[index_buf])+'mV '+'Done.\n') 
                    
                    
                    self.LockState.setText('') 
                    self.LockState.setStyleSheet('background-color:gray')    
                    self.LockPoint_Run.setEnabled(True) 
                    self.LockPoint_Stop.setEnabled(False)   
                    self.Calibrate_XP_DitherAmp.setChecked(False) #修改   
            # @MinMinQuad                           
            elif self.Lock_MinMinQuad_EN.isChecked() == True and self.Calibrate_XP_DitherAmp.isChecked() == True:   
                Min_DitherAmp = self.setting_CDM.value("setup_Calibrate_Locking/Min_DitherAmp_MinMinQuad")
                Max_DitherAmp = self.setting_CDM.value("setup_Calibrate_Locking/Max_DitherAmp_MinMinQuad")                   
                    
                Amp_Step = self.setting_CDM.value("setup_Calibrate_Locking/Step_DitherAmp_MinMinQuad")                
                Flag_1st = self.setting_CDM.value("setup_Calibrate_Locking/Flag_1st") 
                #第一次循环，设置扫描的Amp值
                if Flag_1st == True:
                    
                    report_text = 'For Calibrate@DitherAmp'
                    self.textBroswerPrintRealTime(report_text+' Need LockingLoop num: '+str( (int(Max_DitherAmp) - int(Min_DitherAmp)) ))
                    
                    Amp = int(Min_DitherAmp)
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Current_DitherAmp", Amp) 
                    #第一次启动 校准校准，需要在Min_DitherAmp运行之前，初始化部分参数
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st",False) #置位，防止后续重复进入第一次启动的配置中
                    
                    CDM_SN = self.setting_CDM.value("setup/CDM_SN")
                    self.CDM_T0_Value = self.setting_CDM.value("setup/T0")
                    self.CDM_WL0_Value = round(float(round(float(self.setting_CDM.value("setup/WL0")),1)),1)      
                    folder_path = './log/' + CDM_SN + '/' + CDM_SN +'_'+ str(self.CDM_T0_Value) +'c_'+ str(self.CDM_WL0_Value)+'/' + 'Calibrate_DitherAmp'+ '/'
                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path)
                        # self.textBroswerPrintRealTime("文件夹创建成功")
                    else:
                        # self.textBroswerPrintRealTime("文件夹已存在")
                        None    
                    FileName = folder_path +'RecordPower_For_Calibrate_DitherAmp_MinMinQuad_'+MZ_Channel_name+'_'+ self.Time_text()+'.csv'        
                    self.setting_CDM.setValue("setup_Calibrate_Locking/FileName",FileName)
                    
                    header_buf = ['1mV','2mV','3mV','4mV','5mV','6mV','7mV','8mV','9mV','10mV','11mV','12mV',\
                                    '13mV','14mV','15mV','16mV','17mV','18mV','19mV','20mV','Avg']
                    
                    Amp_Array_buf =  np.arange(int(Min_DitherAmp), int(Max_DitherAmp),2)
                    
                    header = ['']*(len(Amp_Array_buf)+1)
                    for i in range(len(Amp_Array_buf)):
                            header[i] = header_buf[ int(Amp_Array_buf[i])-1 ]
                    header[len(Amp_Array_buf)] = header_buf[20]
                    # print(header)
                    with open(FileName, 'a', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(header)
                        csvfile.close()                   

                else:#其他 Threshold 的循环中，只需使用同样的参数
                    
                    FileName = self.setting_CDM.value("setup_Calibrate_Locking/FileName")
                    #接收 来自循环进程自动增加Amp_Step步进后的 Amp幅度     
                    Amp = int(float(self.setting_CDM.value("setup_Calibrate_Locking/Current_DitherAmp"))   ) 
                      
                if Amp < int(Max_DitherAmp):#确保 到达门限的上限  停止继续循环 
                    #设置Lockthreshold范围:3~12mV,步进1MV，每个步进对应锁定50次且取光功率的平均值作为比较值，该值最小则对应的Lockthreshold为锁定目标
                    #依次为 设置->IQ->Ph->IQ->Ph->IQ->Ph
                    #开始 IQ锁定门限的确认        
                    
                    self.textBroswerPrintRealTime('\nCurrent_'+MZ_Channel_name+'_DitherAmp: '+ str(Amp)+'mV, '+'loop: '+str(Amp - int(Min_DitherAmp)+1)) 
                    
                    self.XP_LockDither_Set_cb( 1, Amp, Amp, self.print_info_no)#修改
                    self.XP_LockDither_Rd_cb( self.print_info_no)#修改

                    #创建一个数组,分配各个元素的长度
                    array_element_BitNum = ['']*5
                    array_element_BitNum[0] = 1*6#cmd
                    
                    array_element_BitNum[1] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
                    array_element_BitNum[2] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
                    array_element_BitNum[3] = 6*(6+2) #每个元素一次性读取  WordNum*6个字节的长数据+ 一个EXPD_flag、一个EXPD ADC

                    array_element_BitNum[4] = 1*6#所有数据接收完成，'AFAF'
                    
                    self.Uart.Rx_data_WordNum_array.emit(array_element_BitNum)#传递给Uart

                    #传输 参数
                    print_info_buf = ['']*3
                    
                    print_info_buf[0] = 20  #标记数据的个数:1*cmd+6*heaterDA+6*平均导数值+6*实时导数值+1*"AFAF"
                    print_info_buf[1] = self.print_info_no[1]
                    print_info_buf[2] = self.print_info_no[2]
                    
                    self.Refresh_COM_settings(False,'LockPoint')#设置串口响应时间

                    text = report_text1+', '+ report_text2
                    self.textBroswerPrintRealTime(text)                  
            
                    action = text        

                    self.Lock_TimeStart = str(self.Time_text())#记录开始锁定的时间
                    self.textBroswerPrintRealTime('StartTime: '+self.Lock_TimeStart)
                    self.textBroswerPrintRealTime('锁定中.../doing Locking...')
                                    
                    self.LongTimeCmd_QThread.LockCycle_Target = LockCycle_Target
                    self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_XY_Lock, print_info_buf, self.Rx_Array, self.FindPoint_Record_length, 
                                                       self.DoLocking_Flag, FileName, FileName_HeaterR, 
                                                       self.CalibrateLocking_Flag, self.record_Power, float(Amp), float(Amp_Step))
                    #启动轮询线程, 包含了SendCmd和数据处理
                    #锁定50次并记录光功率
                    self.LongTimeCmd_QThread.start()  

                else:
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st", True) 
                    self.textBroswerPrintRealTime('\nCalibrate_'+MZ_Channel_name+'_DitherAmp @MinMinQuad Done', self.print_info_fast)

                    # #保存 平均值 数据
                    self.record_Avg_Value =[-100]*(int(Max_DitherAmp) - int(Min_DitherAmp)) 
                           
                    #col列*row行的二维数组
                    #对应(Min_DitherAmp,Max_DitherAmp)mV为需要设置的常规列数，再加1列保存前面10列数(所采数的光功率值)各自平均的结果
                    col = (int(Max_DitherAmp) - int(Min_DitherAmp) +1)
                    row = int(self.setting_CDM.value("setup_Calibrate_Locking/Calibrate_Loop_Cycle")) 
                                
                    self.record_Power =  [[0] * row for _ in range(col)]#二维矩阵                    

                    # 打开CSV文件
                    with open(FileName, mode='r', encoding='utf-8') as csvfile:
                        # 创建csv.reader对象
                        csv_reader = csv.reader(csvfile)
                        # 读取CSV文件的头部
                        header = next(csv_reader)
                        # 逐行读取数据
                        i=0
                        for row in csv_reader:
                            self.record_Power[i] = row # row是一个列表，包含了当前行的所有数据
                            self.record_Avg_Value[i] = self.Calibrate_DitherAmp_Array_Processing(self.record_Power[i])#50次循环锁定的光功率值，取平均值
                            # print(self.record_Power[i],self.record_Avg_Value[i])
                            i = i+1
                        csvfile.close()#关闭文档  
                         
                    # 检查文件是否存在,进行删除，在下一步再进行文档的重新创建和数据的重新保存
                    if os.path.exists(FileName):
                        # 删除文件
                        os.remove(FileName)
                        # print(f"{FileName} has been deleted.")
                    else:
                        # print(f"{FileName} does not exist.") 
                        pass             
                       
                    #将平均值的结果合并进self.record_Power的最后一列
                    for i in range (len(self.record_Avg_Value)):
                        self.record_Power[col-1][i] = self.record_Avg_Value[i]
                            
                    #所有数据存进CSV
                    data = list(zip(*self.record_Power))  # 行列转换
                    # write in DAdata   
                    with open(FileName, 'a', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(header)
                        for i in data:#  write in CSV
                            writer.writerow(i)
                        csvfile.close()    
                    
                    #结束 IQ锁定门限的锁定扫描
                    #开始数据处理
                    index_buf = self.Find_MinValue_Index(self.record_Avg_Value)
                
                    # Amp_Array_buf =  np.arange(int(Min_DitherAmp), int(Max_DitherAmp))

                    self.XP_LockDither_Set_cb( 1, Amp_Array_buf[index_buf], Amp_Array_buf[index_buf], self.print_info_no)#修改
                    self.XP_LockDither_Rd_cb( self.print_info_no)#修改      
                    
                    self.textBroswerPrintRealTime('Set '+MZ_Channel_name+' DitherAmp: '+ str(Amp_Array_buf[index_buf])+'mV '+'Done.') 

                    self.LockState.setText('') 
                    self.LockState.setStyleSheet('background-color:gray')    
                    self.LockPoint_Run.setEnabled(True) 
                    self.LockPoint_Stop.setEnabled(False)  
                    self.Calibrate_XP_DitherAmp.setChecked(False) #修改  
            else:
                self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st", True) 
                self.LockState.setText('') 
                self.LockState.setStyleSheet('background-color:gray')  
                self.LockPoint_Run.setEnabled(True) 
                self.LockPoint_Stop.setEnabled(False)   
                self.Calibrate_XP_DitherAmp.setChecked(False) #修改  
                
    def Calibrate_YP_DitherAmp_cb(self):
        #For Calibrate@DitherAmp
        self.LockState.setStyleSheet('background-color:yellow') #rgb(0, 255, 00)  
        self.LockPoint_Run.setEnabled(False)  # 灰色
        self.LockPoint_Stop.setEnabled(True)            

        #For Calibrate@DitherAmp
        LockCycle_Target = int(self.setting_CDM.value("setup_Calibrate_Locking/Calibrate_Loop_Cycle"))
        Amp_Array_buf = ''
        #修改
        MZ_Channel_name = 'YP'
        self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_MZ_Channel", 4) #置位，在循环进制中，对应选择回调信号 YP=4
        
        self.DoLocking_Flag = True  
        self.CalibrateLocking_Flag = True
        cmd_text = 'AA 01 F1 01 10 00'
        report_text1 = 'All MZ Loop_Lock Begin...'
        report_text2 = 'Change '+ MZ_Channel_name +' DitherAmp' 
        FileName = ''
        FileName_HeaterR = ''
        #创建数组，接收光功率计的值
        num = int( self.setting_CDM.value("setup_Calibrate_Locking/Calibrate_Loop_Cycle") )
        self.record_Power =['']*num  
        Amp = 0
        #需要确保先连接 光功率计
        if self.setting.value("setup_PowerMeter/Flag_Connect_OpticalPower") == False:
            self.textBroswerPrintRealTime('Please Connect PowerMeter')
            self.LockState.setStyleSheet('background-color:gray') #rgb(0, 255, 00)  
            self.LockPoint_Run.setEnabled(True)  # 灰色
            self.LockPoint_Stop.setEnabled(False)    
            self.Calibrate_YP_DitherAmp.setChecked(False)   #修改            
        elif self.CalibrateLocking_Flag == True:
            # @MaxMaxMax #按最大光功率扫描锁定门限
            if self.Lock_MaxMaxMax_EN.isChecked() == True and self.Calibrate_YP_DitherAmp.isChecked() == True:          #修改
                Min_DitherAmp = self.setting_CDM.value("setup_Calibrate_Locking/Min_DitherAmp_MaxMaxMax")
                Max_DitherAmp = self.setting_CDM.value("setup_Calibrate_Locking/Max_DitherAmp_MaxMaxMax")                   
                    
                Amp_Step = self.setting_CDM.value("setup_Calibrate_Locking/Step_DitherAmp_MaxMaxMax")    
                Flag_1st = self.setting_CDM.value("setup_Calibrate_Locking/Flag_1st") 
                
                #第一次循环，设置扫描的Amp值
                if Flag_1st == True:

                    report_text = 'For Calibrate@DitherAmp'
                    self.textBroswerPrintRealTime(report_text+' Need LockingLoop num: '+str( (int(Max_DitherAmp) - int(Min_DitherAmp)) ))
                    
                    Amp = int(Min_DitherAmp)
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Current_DitherAmp", Amp) 
                    #第一次启动 校准校准，需要在Min_DitherAmp运行之前，初始化部分参数
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st",False) #置位，防止后续重复进入第一次启动的配置中
                    
                    CDM_SN = self.setting_CDM.value("setup/CDM_SN")
                    self.CDM_T0_Value = self.setting_CDM.value("setup/T0")
                    self.CDM_WL0_Value = round(float(round(float(self.setting_CDM.value("setup/WL0")),1)),1)      
                    folder_path = './log/' + CDM_SN + '/' + CDM_SN +'_'+ str(self.CDM_T0_Value) +'c_'+ str(self.CDM_WL0_Value)+'/' + 'Calibrate_DitherAmp'+ '/'
                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path)
                        # self.textBroswerPrintRealTime("文件夹创建成功")
                    else:
                        # self.textBroswerPrintRealTime("文件夹已存在")
                        None    
                    FileName = folder_path +'RecordPower_For_Calibrate_DitherAmp_MaxMaxMax_'+MZ_Channel_name+'_'+ self.Time_text()+'.csv'        
                    self.setting_CDM.setValue("setup_Calibrate_Locking/FileName",FileName)
                    
                    header_buf = ['1mV','2mV','3mV','4mV','5mV','6mV','7mV','8mV','9mV','10mV','11mV','12mV',\
                                    '13mV','14mV','15mV','16mV','17mV','18mV','19mV','20mV','Avg']
                    
                    Amp_Array_buf =  np.arange(int(Min_DitherAmp), int(Max_DitherAmp),2)
                    
                    header = ['']*(len(Amp_Array_buf)+1)
                    for i in range(len(Amp_Array_buf)):
                            header[i] = header_buf[ int(Amp_Array_buf[i])-1 ]
                    header[len(Amp_Array_buf)] = header_buf[20]
                    # print(header)
                    with open(FileName, 'a', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(header)
                        csvfile.close()                   

                else:#其他 Threshold 的循环中，只需使用同样的参数
                    FileName = self.setting_CDM.value("setup_Calibrate_Locking/FileName")
                    #接收 来自循环进程自动增加Amp_Step步进后的 Amp幅度     
                    Amp = int(float(self.setting_CDM.value("setup_Calibrate_Locking/Current_DitherAmp"))   )  
                if Amp < int(Max_DitherAmp):#确保 到达门限的上限  停止继续循环 
                    #设置Lockthreshold范围:3~12mV,步进1MV，每个步进对应锁定50次且取光功率的平均值作为比较值，该值最小则对应的Lockthreshold为锁定目标
                    #依次为 设置->IQ->Ph->IQ->Ph->IQ->Ph
                    #开始 IQ锁定门限的确认        
                    
                    self.textBroswerPrintRealTime('\nCurrent_'+MZ_Channel_name+'_DitherAmp: '+ str(Amp)+'mV, '+'loop: '+str(Amp - int(Min_DitherAmp)+1) ) 

                    self.YP_LockDither_Set_cb( 1, Amp, Amp, self.print_info_no)#修改
                    self.YP_LockDither_Rd_cb( self.print_info_no)#修改
                    #创建一个数组,分配各个元素的长度
                    array_element_BitNum = ['']*5
                    array_element_BitNum[0] = 1*6#cmd
                    
                    array_element_BitNum[1] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
                    array_element_BitNum[2] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
                    array_element_BitNum[3] = 6*(6+2) #每个元素一次性读取  WordNum*6个字节的长数据+ 一个EXPD_flag、一个EXPD ADC

                    array_element_BitNum[4] = 1*6#所有数据接收完成，'AFAF'
                    
                    self.Uart.Rx_data_WordNum_array.emit(array_element_BitNum)#传递给Uart

                    #传输 参数
                    print_info_buf = ['']*3
                    
                    print_info_buf[0] = 20  #标记数据的个数:1*cmd+6*heaterDA+6*平均导数值+6*实时导数值+1*"AFAF"
                    print_info_buf[1] = self.print_info_no[1]
                    print_info_buf[2] = self.print_info_no[2]
                    
                    self.Refresh_COM_settings(False,'LockPoint')#设置串口响应时间

                    text = report_text1+', '+ report_text2
                    self.textBroswerPrintRealTime(text)                  
            
                    action = text        

                    self.Lock_TimeStart = str(self.Time_text())#记录开始锁定的时间
                    self.textBroswerPrintRealTime('StartTime: '+self.Lock_TimeStart)
                    self.textBroswerPrintRealTime('锁定中.../doing Locking...')
                            
                    self.LongTimeCmd_QThread.LockCycle_Target = LockCycle_Target
                    self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_XY_Lock, print_info_buf, self.Rx_Array, self.FindPoint_Record_length, 
                                                       self.DoLocking_Flag, FileName, FileName_HeaterR, 
                                                       self.CalibrateLocking_Flag, self.record_Power, float(Amp), float(Amp_Step))
                    #启动轮询线程, 包含了SendCmd和数据处理
                    #锁定50次并记录光功率
                    self.LongTimeCmd_QThread.start()  
                else:
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st", True) 
                    self.textBroswerPrintRealTime('\nCalibrate_'+MZ_Channel_name+'_DitherAmp @MaxMaxMax Done', self.print_info_fast)

                    # #保存 平均值 数据
                    self.record_Avg_Value =[-100]*(int(Max_DitherAmp) - int(Min_DitherAmp)) 
                           
                    #col列*row行的二维数组
                    #对应(Min_DitherAmp,Max_DitherAmp)mV为需要设置的常规列数，再加1列保存前面10列数(所采数的光功率值)各自平均的结果
                    col = (int(Max_DitherAmp) - int(Min_DitherAmp) +1)
                    row = int(self.setting_CDM.value("setup_Calibrate_Locking/Calibrate_Loop_Cycle")) 
                                
                    self.record_Power =  [[0] * row for _ in range(col)]#二维矩阵                    

                    # 打开CSV文件
                    with open(FileName, mode='r', encoding='utf-8') as csvfile:
                        # 创建csv.reader对象
                        csv_reader = csv.reader(csvfile)
                        # 读取CSV文件的头部
                        header = next(csv_reader)
                        # 逐行读取数据
                        i=0
                        for row in csv_reader:
                            self.record_Power[i] = row # row是一个列表，包含了当前行的所有数据
                            self.record_Avg_Value[i] = self.Calibrate_DitherAmp_Array_Processing(self.record_Power[i])#50次循环锁定的光功率值，取平均值
                            # print(self.record_Power[i],self.record_Avg_Value[i])
                            i = i+1
                        csvfile.close()#关闭文档  
                        
                    # 检查文件是否存在,进行删除，在下一步再进行文档的重新创建和数据的重新保存
                    if os.path.exists(FileName):
                        # 删除文件
                        os.remove(FileName)
                        # print(f"{FileName} has been deleted.")
                    else:
                        # print(f"{FileName} does not exist.") 
                        pass            
                    sleep(0.1)
                        
                    #将平均值的结果合并进self.record_Power的最后一列
                    for i in range (len(self.record_Avg_Value)):
                        self.record_Power[col-1][i] = self.record_Avg_Value[i]
                            
                    #所有数据存进CSV
                    data = list(zip(*self.record_Power))  # 行列转换
                    # write in DAdata   
                    with open(FileName, 'a', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(header)
                        for i in data:#  write in CSV
                            writer.writerow(i)
                        csvfile.close()    
                    
                    #结束 IQ锁定门限的锁定扫描
                    #开始数据处理
                    index_buf = self.Find_MaxValue_Index(self.record_Avg_Value)
                    print(index_buf)
                    # Amp_Array_buf =  np.arange(int(Min_DitherAmp), int(Max_DitherAmp))

                    self.YP_LockDither_Set_cb( 1, Amp_Array_buf[index_buf], Amp_Array_buf[index_buf], self.print_info_no)#修改
                    self.YP_LockDither_Rd_cb( self.print_info_no)#修改      
                    
                    self.textBroswerPrintRealTime('Set '+MZ_Channel_name+' DitherAmp: '+ str(Amp_Array_buf[index_buf])+'mV '+'Done.') 

                    self.LockState.setText('') 
                    self.LockState.setStyleSheet('background-color:gray')    
                    self.LockPoint_Run.setEnabled(True) 
                    self.LockPoint_Stop.setEnabled(False)   
                    self.Calibrate_YP_DitherAmp.setChecked(False)   #修改 
             
            elif self.Lock_MinMinQuad_EN.isChecked() == True and self.Calibrate_YP_DitherAmp.isChecked() == True:   #修改
                Min_DitherAmp = self.setting_CDM.value("setup_Calibrate_Locking/Min_DitherAmp_MinMinQuad")
                Max_DitherAmp = self.setting_CDM.value("setup_Calibrate_Locking/Max_DitherAmp_MinMinQuad")                   
                    
                Amp_Step = self.setting_CDM.value("setup_Calibrate_Locking/Step_DitherAmp_MinMinQuad")    
                Flag_1st = self.setting_CDM.value("setup_Calibrate_Locking/Flag_1st") 
                #第一次循环，设置扫描的Amp值
                if Flag_1st == True:

                    report_text = 'For Calibrate@DitherAmp'
                    self.textBroswerPrintRealTime(report_text+' Need LockingLoop num: '+str( (int(Max_DitherAmp) - int(Min_DitherAmp)) ))
                    
                    Amp = int(Min_DitherAmp)
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Current_DitherAmp", Amp) 
                    #第一次启动 校准校准，需要在Min_DitherAmp运行之前，初始化部分参数
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st",False) #置位，防止后续重复进入第一次启动的配置中
                    
                    CDM_SN = self.setting_CDM.value("setup/CDM_SN")
                    self.CDM_T0_Value = self.setting_CDM.value("setup/T0")
                    self.CDM_WL0_Value = round(float(round(float(self.setting_CDM.value("setup/WL0")),1)),1)      
                    folder_path = './log/' + CDM_SN + '/' + CDM_SN +'_'+ str(self.CDM_T0_Value) +'c_'+ str(self.CDM_WL0_Value)+'/' + 'Calibrate_DitherAmp'+ '/'
                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path)
                        # self.textBroswerPrintRealTime("文件夹创建成功")
                    else:
                        # self.textBroswerPrintRealTime("文件夹已存在")
                        None    
                    FileName = folder_path +'RecordPower_For_Calibrate_DitherAmp_MinMinQuad_'+MZ_Channel_name+'_'+ self.Time_text()+'.csv'        
                    self.setting_CDM.setValue("setup_Calibrate_Locking/FileName",FileName)
                    
                    header_buf = ['1mV','2mV','3mV','4mV','5mV','6mV','7mV','8mV','9mV','10mV','11mV','12mV',\
                                    '13mV','14mV','15mV','16mV','17mV','18mV','19mV','20mV','Avg']
                    
                    Amp_Array_buf =  np.arange(int(Min_DitherAmp), int(Max_DitherAmp),2)
                    
                    header = ['']*(len(Amp_Array_buf)+1)
                    for i in range(len(Amp_Array_buf)):
                            header[i] = header_buf[ int(Amp_Array_buf[i])-1 ]
                    header[len(Amp_Array_buf)] = header_buf[20]
                    # print(header)
                    with open(FileName, 'a', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(header)
                        csvfile.close()                   

                else:#其他 Threshold 的循环中，只需使用同样的参数
                    
                    FileName = self.setting_CDM.value("setup_Calibrate_Locking/FileName")
                    #接收 来自循环进程自动增加Amp_Step步进后的 Amp幅度     
                    Amp = int(float(self.setting_CDM.value("setup_Calibrate_Locking/Current_DitherAmp"))   )  

                if Amp < int(Max_DitherAmp):#确保 到达门限的上限  停止继续循环 
                    #设置Lockthreshold范围:3~12mV,步进1MV，每个步进对应锁定50次且取光功率的平均值作为比较值，该值最小则对应的Lockthreshold为锁定目标
                    #依次为 设置->IQ->Ph->IQ->Ph->IQ->Ph
                    #开始 IQ锁定门限的确认        
                    self.textBroswerPrintRealTime('\nCurrent_'+MZ_Channel_name+'_DitherAmp: '+ str(Amp)+'mV, '+'loop: '+str(Amp - int(Min_DitherAmp)+1) ) 
                    self.YP_LockDither_Set_cb( 1, Amp, Amp, self.print_info_no)#修改
                    self.YP_LockDither_Rd_cb( self.print_info_no)#修改


                    #创建一个数组,分配各个元素的长度
                    array_element_BitNum = ['']*5
                    array_element_BitNum[0] = 1*6#cmd
                    
                    array_element_BitNum[1] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
                    array_element_BitNum[2] = 6*6 #每个元素一次性读取  WordNum*6个字节的长数据 
                    array_element_BitNum[3] = 6*(6+2) #每个元素一次性读取  WordNum*6个字节的长数据+ 一个EXPD_flag、一个EXPD ADC

                    array_element_BitNum[4] = 1*6#所有数据接收完成，'AFAF'
                    
                    self.Uart.Rx_data_WordNum_array.emit(array_element_BitNum)#传递给Uart

                    #传输 参数
                    print_info_buf = ['']*3
                    
                    print_info_buf[0] = 20  #标记数据的个数:1*cmd+6*heaterDA+6*平均导数值+6*实时导数值+1*"AFAF"
                    print_info_buf[1] = self.print_info_no[1]
                    print_info_buf[2] = self.print_info_no[2]
                    
                    self.Refresh_COM_settings(False,'LockPoint')#设置串口响应时间

                    text = report_text1+', '+ report_text2
                    self.textBroswerPrintRealTime(text)                  
            
                    action = text        

                    self.Lock_TimeStart = str(self.Time_text())#记录开始锁定的时间
                    self.textBroswerPrintRealTime('StartTime: '+self.Lock_TimeStart)
                    self.textBroswerPrintRealTime('锁定中.../doing Locking...')
                            
                    self.LongTimeCmd_QThread.LockCycle_Target = LockCycle_Target
                    self.LongTimeCmd_QThread.Info_Copy(cmd_text, action, self.Action_Num_XY_Lock, print_info_buf, self.Rx_Array, self.FindPoint_Record_length, 
                                                       self.DoLocking_Flag, FileName, FileName_HeaterR, 
                                                       self.CalibrateLocking_Flag, self.record_Power, float(Amp), float(Amp_Step))
                    #启动轮询线程, 包含了SendCmd和数据处理
                    #锁定50次并记录光功率
                    self.LongTimeCmd_QThread.start()  
                else:
                    self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st", True) 
                    self.textBroswerPrintRealTime('\nCalibrate_'+MZ_Channel_name+'_DitherAmp @MinMinQuad Done', self.print_info_fast)

                    # #保存 平均值 数据
                    self.record_Avg_Value =[-100]*(int(Max_DitherAmp) - int(Min_DitherAmp)) 
                           
                    #col列*row行的二维数组
                    #对应(Min_DitherAmp,Max_DitherAmp)mV为需要设置的常规列数，再加1列保存前面10列数(所采数的光功率值)各自平均的结果
                    col = (int(Max_DitherAmp) - int(Min_DitherAmp) +1)
                    row = int(self.setting_CDM.value("setup_Calibrate_Locking/Calibrate_Loop_Cycle")) 
                                
                    self.record_Power =  [[0] * row for _ in range(col)]#二维矩阵                    

                    # 打开CSV文件
                    with open(FileName, mode='r', encoding='utf-8') as csvfile:
                        # 创建csv.reader对象
                        csv_reader = csv.reader(csvfile)
                        # 读取CSV文件的头部
                        header = next(csv_reader)
                        # 逐行读取数据
                        i=0
                        for row in csv_reader:
                            self.record_Power[i] = row # row是一个列表，包含了当前行的所有数据
                            self.record_Avg_Value[i] = self.Calibrate_DitherAmp_Array_Processing(self.record_Power[i])#50次循环锁定的光功率值，取平均值
                            # print(self.record_Power[i],self.record_Avg_Value[i])
                            i = i+1
                        csvfile.close()#关闭文档  
                        
                    # 检查文件是否存在,进行删除，在下一步再进行文档的重新创建和数据的重新保存
                    if os.path.exists(FileName):
                        # 删除文件
                        os.remove(FileName)
                        # print(f"{FileName} has been deleted.")
                    else:
                        # print(f"{FileName} does not exist.") 
                        pass            
                    sleep(0.1)
                        
                    #将平均值的结果合并进self.record_Power的最后一列
                    for i in range (len(self.record_Avg_Value)):
                        self.record_Power[col-1][i] = self.record_Avg_Value[i]
                            
                    #所有数据存进CSV
                    data = list(zip(*self.record_Power))  # 行列转换
                    # write in DAdata   
                    with open(FileName, 'a', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(header)
                        for i in data:#  write in CSV
                            writer.writerow(i)
                        csvfile.close()    
                    
                    #结束 IQ锁定门限的锁定扫描
                    #开始数据处理
                    index_buf = self.Find_MinValue_Index(self.record_Avg_Value)
                
                    # Amp_Array_buf =  np.arange(int(Min_DitherAmp), int(Max_DitherAmp))

                    self.YP_LockDither_Set_cb( 1, Amp_Array_buf[index_buf], Amp_Array_buf[index_buf], self.print_info_no)#修改
                    self.YP_LockDither_Rd_cb( self.print_info_no)#修改      

                    self.textBroswerPrintRealTime('Set '+MZ_Channel_name+' DitherAmp: '+ str(Amp_Array_buf[index_buf])+'mV '+'Done.\n') 

                    self.LockState.setText('') 
                    self.LockState.setStyleSheet('background-color:gray')    
                    self.LockPoint_Run.setEnabled(True) 
                    self.LockPoint_Stop.setEnabled(False)   
                    self.Calibrate_YP_DitherAmp.setChecked(False)   #修改
                    
            else:
                self.setting_CDM.setValue("setup_Calibrate_Locking/Flag_1st", True) 
                self.LockState.setText('') 
                self.LockState.setStyleSheet('background-color:gray')  
                self.LockPoint_Run.setEnabled(True) 
                self.LockPoint_Stop.setEnabled(False)   
                self.Calibrate_YP_DitherAmp.setChecked(False)   #修改
                
    def Calibrate_DitherAmp_Array_Processing(self, Array):
        sum = 0
        avg = 0
        num = len(Array)
        for i in range (len(Array)):
            if Array[i] != '' and Array[i] != 'NA':
                sum = sum + float(Array[i])
            else:
                num = num - 1
        avg = sum/(len(Array)*1.0)
        return avg

    def Find_MaxValue_Index(self,lst):
        max_value = max(lst)
        max_index = lst.index(max_value)
        return max_index
    def Find_MinValue_Index(self,lst):
        min_value = min(lst)
        min_index = lst.index(min_value)
        return min_index
                           


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    window = LockPiont_Pane()
    # window.exit_signal.connect(lambda:print('cc'))
    # window.register_signal.connect(lambda a,p : print(a,p))
    
    # window.check_serial_ports(window.SerialPortB)
    window.show()

    sys.exit(app.exec_())
