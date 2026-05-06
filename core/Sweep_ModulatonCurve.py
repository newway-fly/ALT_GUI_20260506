# -*- coding: utf-8 -*-
#导入包和模块 pip install pylance -i https://pypi.tuna.tsinghua.edu.cn/simple/
#pip install serial -i http://pypi.douban.com/simple/

from PyQt5 import QtWidgets,QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtCore import pyqtSignal,QThread
import matplotlib.pyplot as plt
import sys, datetime,csv,os
sys.path.append(os.getcwd())
import sys, datetime,re
from utils.Ui_Sweep_ModulationCurve import Ui_Sweep_ModulationCurve
from utils.TCPIP import TCPIP_Socket
from time import sleep


#所有变量以字符串格式进行传递（可以是16进制或者10进制，变量名带上识别_7hex/_int）

class Sweep_ModulatinCurve(QtWidgets.QWidget, Ui_Sweep_ModulationCurve ):
    
    LogPrint = pyqtSignal(str, list)
    RebackData = pyqtSignal(str)
    RebackDone = pyqtSignal()    
    
    
    def __init__(self, parent=None, *args,**kwargs):#该类一旦实例化，第一时间执行的内容      
        super().__init__(parent, *args,**kwargs)#        
        self.setupUi(self)


        # 设备配置文件的路径 加载内容
        self.setting = QtCore.QSettings("./data/config_Board.ini", QtCore.QSettings.IniFormat)
        self.setting .setIniCodec("UTF-8")#设置格式
        # 设置CDM配置文件的路径 加载内容
        self.setting_CDM = QtCore.QSettings("./data/config_CDM.ini", QtCore.QSettings.IniFormat)
        self.setting_CDM .setIniCodec("UTF-8")#设置格式   
        
        self.ModulationCurve_StartDA.setText(self.setting_CDM.value("setup_ModulationCurve/StartDA"))         
        self.ModulationCurve_SweepRange.setText(self.setting_CDM.value("setup_ModulationCurve/SweepRange"))   
        self.ModulationCurve_SweepPoint.setText(self.setting_CDM.value("setup_ModulationCurve/SweepPoint")) 
        self.ModulationCurve_FirstPoint_Wait.setText(self.setting_CDM.value("setup_ModulationCurve/FirstPoint_Wait")) 

        self.PowerMeter_Ch_num = ''
        self.PowerMeter_Port_num = ''
        self.PowerMeter_WL_num = ''
        self.PowerMeter_Unit = ''
        self.PowerMeter_Ch_num = self.setting.value("setup_PowerMeter/PowerMeter_Ch")
        self.PowerMeter_Port_num = self.setting.value("setup_PowerMeter/PowerMeter_Port")
        self.PowerMeter_WL_num = self.setting.value("setup_PowerMeter/PowerMeter_WL")
        self.PowerMeter_Unit = self.setting.value("setup_PowerMeter/PowerMeter_Unit")  
        self.setting.setValue("setup_PowerMeter/Flag_Connect_OpticalPower",False) 
        self.setting.setValue("setup_PowerMeter/Flag_OpticalPower_Change", False)

        self.QLineEdit_TCPIP.setText(self.setting.value("setup_PowerMeter/PowerMeter_TCPIP")) 

        self.PowerMeter_Ch.setText(self.PowerMeter_Ch_num)
        self.PowerMeter_Port.setText(self.PowerMeter_Port_num)
        self.PowerMeter_WL.setText(self.PowerMeter_WL_num)
        
        self.BiasVolt_ranege = 0
        self.MZ_Channel= ''
        self.MZ_Channel_num = 0
        self.DA_I_shift_ch = '0'
        self.DA_Q_shift_ch = '0'
        self.DA_I_shift = "0"
        self.DA_Q_shift = "0"
        self.DA_I = "0"
        self.DA_Q = "0"       
        self.Phase_Sweep = ['']*6
        
        # 实例化
        self.PowerMeter_Control = TCPIP_Socket()
        self.Sweep_QThread = QThread_SendCmd_SelPrint()
        
        self.Sweep_QThread.CmdTransfer_GetData.connect(self.SendCmd_GetData)
   
        self.RebackData.connect(self.Sweep_QThread.RebackData_Save)
        self.Sweep_QThread.Loop_Done.connect(self.Loop_Done_cb)  
        self.Sweep_QThread.LogPrint.connect(self.textBroswerPrintRealTime)      
        # self.Sweep_QThread.Cmd_SetDAC.connect(self.Cmd_SetDAC_cb)
        
        
        self.Loop_ReadPower.clicked.connect(self.loop_ReadPower_cb)
        
        self.pushButton_Connect.clicked.connect(self.Connect_OnOff)
        self.Set_Ch_Port.clicked.connect(self.set_Ch_Port_cb)
        
        self.GetPower.clicked.connect(lambda:self.GetPower_cb())
        
        self.SetWaveLen.clicked.connect(self.SetWaveLen_cb)
        self.ReadWaveLen.clicked.connect(self.ReadWaveLen_cb)
        self.SetUnit_dBm.clicked.connect(lambda:self.SetUnit_cb('dBm'))
        self.SetUnit_mW.clicked.connect(lambda:self.SetUnit_cb('mW'))
        
        self.ModulationCurve_XI.clicked.connect(lambda:self.ChannelSelect('XI'))
        self.ModulationCurve_XQ.clicked.connect(lambda:self.ChannelSelect('XQ'))
        self.ModulationCurve_XP.clicked.connect(lambda:self.ChannelSelect('XP'))
        self.ModulationCurve_YI.clicked.connect(lambda:self.ChannelSelect('YI'))
        self.ModulationCurve_YQ.clicked.connect(lambda:self.ChannelSelect('YQ'))
        self.ModulationCurve_YP.clicked.connect(lambda:self.ChannelSelect('YP'))

        self.Sweep_Start.clicked.connect(self.Sweep_Setup)
        self.Sweep_Stop.clicked.connect(self.Sweep_Stop_cb)     
           
        self.Sweep_Start.setEnabled(True)
        self.Sweep_Stop.setEnabled(False)          
        
    def Connect_OnOff(self):
        
        TCPIP_buf = self.QLineEdit_TCPIP.text() 

        if self.pushButton_Connect.text() == 'Connect' :
            
            flag = self.PowerMeter_Control.setup_newSocket(TCPIP_buf)    
            if flag != False:
                self.textBroswerPrintRealTime(flag.replace('\n',''))
                self.textBroswerPrintRealTime( TCPIP_buf +' Connect OK')
                self.pushButton_Connect.setText('Disconnect')
                self.label_IP.setStyleSheet('background-color:rgb(0, 255, 0)')  
                
                self.setting.setValue("setup_PowerMeter/PowerMeter_TCPIP",self.QLineEdit_TCPIP.text())
                self.ReadUnit_cb() 
                self.setting.setValue("setup_PowerMeter/Flag_Connect_OpticalPower", True)
                
            else: 
                self.textBroswerPrintRealTime(' Connect Failed')
                self.pushButton_Connect.setText('Connect')
                self.label_IP.setStyleSheet('background-color:rgb(255, 255, 255)') 
                
        elif self.pushButton_Connect.text() == 'Disconnect' :
            self.PowerMeter_Control.Socket_Close()
            self.textBroswerPrintRealTime(TCPIP_buf +' Disconnect')
            self.pushButton_Connect.setText('Connect')
            self.label_IP.setStyleSheet('background-color:rgb(255, 255, 255)') 
            self.setting.setValue("setup_PowerMeter/Flag_Connect_OpticalPower", False)

    def Time_text(self):
        return datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    
    def SendCmd_Only(self, cmd=''):
        if cmd == '':
            
            cmd = self.Input_1.text()
            print(cmd)
        flag = self.PowerMeter_Control.SendCmd(cmd)
 
        if flag ==True:
            self.textBroswerPrintRealTime(  cmd +' 发送成功')
        else:
            self.textBroswerPrintRealTime(  cmd +' 发送失败')         
    def SendCmd_GetData(self, cmd='', flag = ''):
        
        Info = self.PowerMeter_Control.SendCmd_GetData(cmd)

        if Info != False:
            if flag == True:
               self.RebackData.emit(str(float(Info)))
            else:
                # self.textBroswerPrintRealTime(  cmd +' 发送成功')
                Info = re.sub(r"\s+", "", Info)
                # self.textBroswerPrintRealTime('response:' + str(Info))                
                return Info
        else:
            self.textBroswerPrintRealTime(  cmd +' 发送失败')
            return False
                # #所有数据存进CSV
                # # data = list(zip(*array_buf))  # 行列转换
                # with open(filename, 'a', encoding='utf-8-sig', newline='') as csvfile:
                #     writer = csv.writer(csvfile)
                #     # writer.writerow(header)
                #     writer.writerow(array_buf)
                #     # for i in data:#  write in CSV
                #     #     writer.writerow(i)
                #     csvfile.close()    

    
    def ChannelSelect(self,Ch):
        #触发回调函数的通道a先 清空除了a通道以外的所有通道的状态
        match Ch:
            case 'XI':
                self.ModulationCurve_XQ.setChecked(False)
                self.ModulationCurve_XP.setChecked(False)
                self.ModulationCurve_YI.setChecked(False)
                self.ModulationCurve_YQ.setChecked(False)
                self.ModulationCurve_YP.setChecked(False)
            case 'XQ':
                self.ModulationCurve_XI.setChecked(False)
                self.ModulationCurve_XP.setChecked(False)
                self.ModulationCurve_YI.setChecked(False)
                self.ModulationCurve_YQ.setChecked(False)
                self.ModulationCurve_YP.setChecked(False)                
            case 'XP':
                self.ModulationCurve_XI.setChecked(False)
                self.ModulationCurve_XQ.setChecked(False)
                self.ModulationCurve_YI.setChecked(False)
                self.ModulationCurve_YQ.setChecked(False)
                self.ModulationCurve_YP.setChecked(False)                
            case 'YI':
                self.ModulationCurve_XI.setChecked(False)
                self.ModulationCurve_XQ.setChecked(False)
                self.ModulationCurve_XP.setChecked(False) 
                self.ModulationCurve_YQ.setChecked(False)
                self.ModulationCurve_YP.setChecked(False)
            case 'YQ':
                self.ModulationCurve_XI.setChecked(False)
                self.ModulationCurve_XQ.setChecked(False)
                self.ModulationCurve_XP.setChecked(False) 
                self.ModulationCurve_YI.setChecked(False)
                self.ModulationCurve_YP.setChecked(False)                  
            case 'YP':
                self.ModulationCurve_XI.setChecked(False)
                self.ModulationCurve_XQ.setChecked(False)
                self.ModulationCurve_XP.setChecked(False) 
                self.ModulationCurve_YI.setChecked(False)
                self.ModulationCurve_YQ.setChecked(False)
                
        #然后判断 a的状态还保留着打勾的状态       
        if self.ModulationCurve_XI.isChecked() == True:
            self.MZ_Channel = 'XI'
            self.MZ_Channel_num = 1
        elif self.ModulationCurve_XQ.isChecked() == True:
            self.MZ_Channel = 'XQ'
            self.MZ_Channel_num = 2
        elif self.ModulationCurve_XP.isChecked() == True:
            self.MZ_Channel = 'XP'
            self.MZ_Channel_num = 5
        elif self.ModulationCurve_YI.isChecked() == True:
            self.MZ_Channel = 'YI'
            self.MZ_Channel_num = 3
        elif self.ModulationCurve_YQ.isChecked() == True:
            self.MZ_Channel = 'YQ'
            self.MZ_Channel_num = 4
        elif self.ModulationCurve_YP.isChecked() == True:
            self.MZ_Channel = 'YP'
            self.MZ_Channel_num = 6
        else:
            self.MZ_Channel = ''
            self.MZ_Channel_num = 0

    
    def set_Ch_Port_cb(self):
        ch = self.PowerMeter_Ch.text()
        Port = self.PowerMeter_Port.text()
        self.setting.setValue("setup_PowerMeter/PowerMeter_Ch", ch)  
        self.setting.setValue("setup_PowerMeter/PowerMeter_Port", Port)  
        self.PowerMeter_Ch_num = self.setting.value("setup_PowerMeter/PowerMeter_Ch")
        self.PowerMeter_Port_num = self.setting.value("setup_PowerMeter/PowerMeter_Port")
    def SetWaveLen_cb(self):
        ch = self.PowerMeter_Ch_num
        port = self.PowerMeter_Port_num
        WL = self.PowerMeter_WL.text()
        command = ':SENS'+str(ch)+':CHAN'+str(port)+':POW:WAV '+str(WL)+'nm' # 设置要发送的命令
        self.SendCmd_Only(command)
        buf = self.ReadWaveLen_cb()
        if WL == buf:
            self.textBroswerPrintRealTime('波长设置成功')
        else:
            self.textBroswerPrintRealTime('波长设置失败')
    def ReadWaveLen_cb(self):
        ch = self.PowerMeter_Ch_num
        port = self.PowerMeter_Port_num
        command = ':SENS'+str(ch)+':CHAN'+str(port)+':POW:WAV?' # 设置要发送的命令
        WL_buf = self.SendCmd_GetData(command)
        WL_buf = str(float(WL_buf)*1e9)[0:6]
        self.textBroswerPrintRealTime('波长:'+WL_buf)  
        self.PowerMeter_WL.setText(WL_buf)  
        self.setting.setValue("setup_PowerMeter/PowerMeter_WL", WL_buf)     
        return WL_buf
    def SetUnit_cb(self,unit):
        ch = self.PowerMeter_Ch_num
        port = self.PowerMeter_Port_num   
        #发送命令到光功率计，获取返回结果。根据光功率计的通信规则，构造合适的命令字符串，并将其转换为bytes类型后发送给光功率计。
        if unit == 'mW':#mW
            unit_num = 1
            command = ':SENS'+str(ch)+':CHAN'+str(port)+':POW:UNIT '+str(unit_num) # 设置要发送的命令
            self.SendCmd_Only(command)
        elif unit == 'dBm':#dBm
            unit_num = 0
            command = ':SENS'+str(ch)+':CHAN'+str(port)+':POW:UNIT '+str(unit_num) # 设置要发送的命令
            self.SendCmd_Only(command)
        buf = self.ReadUnit_cb()
        if unit == buf:
            self.textBroswerPrintRealTime('Unit设置成功')
        else:
            self.textBroswerPrintRealTime('Unit设置失败')
    def ReadUnit_cb(self):#read
        ch = self.PowerMeter_Ch_num
        port = self.PowerMeter_Port_num
        command = ':SENS'+str(ch)+':CHAN'+str(port)+':POW:UNIT?'# 单位设置错误，打印当前的单位类型
        unit_buf = self.SendCmd_GetData(command)
        if int(unit_buf) == 1:
            unit = 'mW'
            self.textBroswerPrintRealTime('Uint: mW') 
            self.SetUnit_mW.setChecked(True)
            self.SetUnit_mW.setStyleSheet('background-color:rgb(0, 255, 0)')  
            self.SetUnit_dBm.setStyleSheet('background-color:rgb(255, 255, 255)') 
            self.setting.setValue("setup_PowerMeter/PowerMeter_Unit", unit) 
            self.PowerMeter_Unit = 'mW'
        elif int(unit_buf) == 0:
            unit = 'dBm'
            self.textBroswerPrintRealTime('Uint: dBm')
            self.SetUnit_dBm.setChecked(True)
            self.SetUnit_dBm.setStyleSheet('background-color:rgb(0, 255, 0)') 
            self.SetUnit_mW.setStyleSheet('background-color:rgb(255, 255, 255)') 
            self.setting.setValue("setup_PowerMeter/PowerMeter_Unit", unit) 
            self.PowerMeter_Unit = 'dBm'
        else:
            unit = 'xxxx'  
            self.textBroswerPrintRealTime('单位类型读取失败') 
        return unit   

    #cmd_type = 0  只记录光功率
    def loop_ReadPower_cb(self):  # textBrowser实时打印信息
        sleep(0.01)
        if self.Loop_ReadPower.isChecked() == True:
            self.Loop_ReadPower_Flag = True
            ch = self.PowerMeter_Ch_num
            port = self.PowerMeter_Port_num
            
            PowerSampling_cmd = ':FETC'+str(ch)+':CHAN'+str(port)+':POW?'
            self.CDM_SN = self.setting_CDM.value("setup/CDM_SN")
            self.CDM_T0_Value = self.setting_CDM.value("setup/T0")
            self.CDM_WL0_Value = round(float(self.setting_CDM.value("setup/WL0")),1)                 
            self.TimeStart = self.Time_text()
            folder_path = './log/' + self.CDM_SN + '/' + self.CDM_SN +'_'+ str(self.CDM_T0_Value) +'C_'+ str(self.CDM_WL0_Value) + '/' +'Loop_ReadPower'
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                # print("文件夹创建成功")
                # self.textBroswerPrintRealTime("文件夹创建成功")
            else:
                # print("文件夹已存在")
                # self.textBroswerPrintRealTime("文件夹已存在")
                None
            
            csv_name        =       self.CDM_SN +'_'+ str(self.CDM_T0_Value) +'C_'+ str(self.CDM_WL0_Value)+'_Loop_ReadPower'+'_'+ self.Time_text() +'.csv'         
            self.filename   =       str(folder_path)+ '/' +  str(csv_name)
            self.filename_polt =    str(folder_path)+ '/' + self.CDM_SN +'_'+ str(self.CDM_T0_Value) +'C_'+ str(self.CDM_WL0_Value)+'_Loop_ReadPower'+'_'+ self.Time_text()
            self.textBroswerPrintRealTime('\n保存路径: '+ str(folder_path))  
            self.textBroswerPrintRealTime('CSV文件名: '+ str(csv_name))  
            
            header = ['Time','Optial_Power']        
            #行头数据存进CSV
            with open(self.filename, 'a', encoding='utf-8-sig', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(header)
                csvfile.close()    
            
            self.TimeStart = self.Time_text()
            cmd_type = 0#只记录光功率
            self.Sweep_QThread.Info_Copy_Loop_ReadPower( PowerSampling_cmd, cmd_type, self.Loop_ReadPower_Flag, self.filename, self.TimeStart) 
            self.Sweep_QThread.start()
        else:
            # self.Loop_ReadPower_Flag = False
            self.Sweep_QThread.Loop_ReadPower_Flag = False
    #cmd_type = 1  记录调制曲线
    def Sweep_Setup(self):#传输数组、文件名等    
        sleep(0.01)
        self.Sweep_Stop_Flag = False
        ch = self.PowerMeter_Ch_num
        port = self.PowerMeter_Port_num
        if self.ModulationCurve_EXPD_Curr.isChecked() == False:
            PowerSampling_cmd = ':FETC'+str(ch)+':CHAN'+str(port)+':POW?'
        else:# 使用外置PD,读取光电流和档位
            PowerSampling_cmd = ''# 直接调用固定ADC读取函数
            self.textBroswerPrintRealTime('EXPD记录调制曲线')
            # PowerSampling_cmd = 'AA 82 F1 AA AA 07'  #返回数据 PD_ResFlag: Rx_Array_buf[6:8], EXPD_Curr：Rx_Array_buf[9:12]
        flag = 0
        #确认 是否具备扫描调制曲线的条件
        if self.setting.value("setup/SerialPortB_ConnectFlag") != True:
            self.textBroswerPrintRealTime('Please Connect SerialPort B!')
            text = 'Please Connect SerialPort B!'
            QtWidgets.QMessageBox.information(self, "提示", text, QMessageBox.Ok | QMessageBox.Close)
        else:
            if self.MZ_Channel == '':
                flag = 1
            if self.pushButton_Connect.text() == 'Connect':
                flag = 2
            if self.MZ_Channel == '' and self.pushButton_Connect.text() == 'Connect':  
                flag = 3
                
        
            if flag != 0:
                if flag == 1: 
                    self.textBroswerPrintRealTime('Please select MZ channel!')
                    text = 'Please select MZ channel!'
                    QtWidgets.QMessageBox.information(self, "提示", text, QMessageBox.Ok | QMessageBox.Close)
                elif flag == 2:
                    self.textBroswerPrintRealTime('Please Connect PowerMeter!')
                    text = 'Please Connect PowerMeter!'
                    QtWidgets.QMessageBox.information(self, "提示", text, QMessageBox.Ok | QMessageBox.Close)       
                else: 
                    self.textBroswerPrintRealTime('Please select MZ channel and Connect PowerMeter!')
                    text = 'Please select MZ channel and Connect PowerMeter!'
                    QtWidgets.QMessageBox.information(self, "提示", text, QMessageBox.Ok | QMessageBox.Close)              
            else:
                MZ_Ch = self.MZ_Channel
                Sweep_ch = self.MZ_Channel_num
                
                #根据配置文件实时更新NNQ数据，读取6ch DA
                #从NNQ，直接开始扫描
                DA_BUF_hex = "0"
                DA_BUF_I_hex = "0"
                DA_BUF_Q_hex = "0"
                match MZ_Ch:
                    case 'XI':
                        DA_BUF_hex = self.setting_CDM.value("LockPoint/LockPoint_XI")
                    case 'XQ':
                        DA_BUF_hex = self.setting_CDM.value("LockPoint/LockPoint_XQ")
                    case 'XP':
                        DA_BUF_hex = self.setting_CDM.value("LockPoint/LockPoint_XP")
                        DA_BUF_I_hex = self.setting_CDM.value("LockPoint/LockPoint_XI")
                        DA_BUF_Q_hex = self.setting_CDM.value("LockPoint/LockPoint_XQ")
                        self.DA_I = int(str(DA_BUF_I_hex),16)
                        self.DA_Q = int(str(DA_BUF_Q_hex),16)
                        if self.ModulationCurve_MMM.isChecked() == True:# MaxMaxMax工作点，IQ无需拉偏
                            self.DA_I_shift = int(str(DA_BUF_I_hex),16)
                            self.DA_Q_shift = int(str(DA_BUF_Q_hex),16)
                        else:
                            self.DA_I_shift = int(str(DA_BUF_I_hex),16)+100
                            self.DA_Q_shift = int(str(DA_BUF_Q_hex),16)+100                            
                        self.DA_I_shift_ch = 1
                        self.DA_Q_shift_ch = 2

                    case 'YI':
                        DA_BUF_hex = self.setting_CDM.value("LockPoint/LockPoint_YI")
                    case 'YQ':
                        DA_BUF_hex = self.setting_CDM.value("LockPoint/LockPoint_YQ")
                    case 'YP':
                        DA_BUF_hex = self.setting_CDM.value("LockPoint/LockPoint_YP")
                        DA_BUF_I_hex = self.setting_CDM.value("LockPoint/LockPoint_YI")
                        DA_BUF_Q_hex = self.setting_CDM.value("LockPoint/LockPoint_YQ")
                        self.DA_I = int(str(DA_BUF_I_hex),16)
                        self.DA_Q = int(str(DA_BUF_Q_hex),16)
                        if self.ModulationCurve_MMM.isChecked() == True:# MaxMaxMax工作点，IQ无需拉偏
                            self.DA_I_shift = int(str(DA_BUF_I_hex),16)
                            self.DA_Q_shift = int(str(DA_BUF_Q_hex),16)                           
                        else:
                            self.DA_I_shift = int(str(DA_BUF_I_hex),16)+100 
                            self.DA_Q_shift = int(str(DA_BUF_Q_hex),16)+100  
                        self.DA_I_shift_ch = 3
                        self.DA_Q_shift_ch = 4
                    
                    
                self.Phase_Sweep[0] = self.DA_I_shift_ch
                self.Phase_Sweep[1] = self.DA_Q_shift_ch
                self.Phase_Sweep[2] = '0x'+f"{int( self.DA_I_shift ):04X}"#转化为带0x的4位16进制数
                self.Phase_Sweep[3] = '0x'+f"{int( self.DA_Q_shift ):04X}"#转化为带0x的4位16进制数
                self.Phase_Sweep[4] = '0x'+f"{int( self.DA_I ):04X}"#转化为带0x的4位16进制数
                self.Phase_Sweep[5] = '0x'+f"{int( self.DA_Q ):04X}"#转化为带0x的4位16进制数

                if self.ModulationCurve_DirectSweep.isChecked() == True:            
                    StartDA = int(str(DA_BUF_hex),16) 
                else:
                    #设置起始DA
                    StartDA = int(self.ModulationCurve_StartDA.text())          #扫描起始DA，int
                    

                ScanRange = int(self.ModulationCurve_SweepRange.text())         #扫描范围，做判断，不能超过最大值
                SweepPoint = int(self.ModulationCurve_SweepPoint.text())        #扫描点数
                StepTime = int(self.ModulationCurve_StepTime.text())/1000.0     #步进时间ms
                StepTime_buf = round(StepTime*1000)
                FirstPoint_Wait = int(self.ModulationCurve_FirstPoint_Wait.text())
                
                #通过文件读取到 bias运放的供电范围，用来限定DA的最大值
                self.BiasVolt_ranege = self.setting.value("setup_BiasVolt_Range/BiasVolt_Range")
                if float(self.BiasVolt_ranege) == 5.0:
                    max_value = 3100
                elif float(self.BiasVolt_ranege) == 6.5:
                    max_value = 4030
                
                DaArray = [''] * SweepPoint  #计算DAC数组
                for i in range(SweepPoint): 
                    buf = StartDA + ScanRange/SweepPoint*i
                    if buf < max_value:
                        DaArray[i] = '0x'+f"{int( buf ):04X}"#转化为带0x的4位16进制数
                    else:
                        DaArray[i] = '0x'+f"{int( 4030 ):04X}"
                
                self.CDM_SN = self.setting_CDM.value("setup/CDM_SN")
                self.CDM_T0_Value = self.setting_CDM.value("setup/T0")
                self.CDM_WL0_Value = round(float(self.setting_CDM.value("setup/WL0")),1)       

                folder_path = './log/' + self.CDM_SN + '/' + self.CDM_SN +'_'+ str(self.CDM_T0_Value) +'C_'+ str(self.CDM_WL0_Value) + '/' +'ModulationCurve'
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                    # print("文件夹创建成功")
                    # self.textBroswerPrintRealTime("文件夹创建成功")
                else:
                    # print("文件夹已存在")
                    # self.textBroswerPrintRealTime("文件夹已存在")
                    pass
                
                csv_name        =       self.CDM_SN +'_'+ str(self.CDM_T0_Value) +'C_'+ str(self.CDM_WL0_Value)+'_ModulationCurve'+'_'+str(MZ_Ch)+'_'+str(StepTime_buf)+'ms_'+ self.Time_text() +'.csv'         
                self.filename   =       str(folder_path)+ '/' +  str(csv_name)
                self.filename_polt =    str(folder_path)+ '/' + self.CDM_SN +'_'+ str(self.CDM_T0_Value) +'C_'+ str(self.CDM_WL0_Value)+'_ModulationCurve'+'_'+str(MZ_Ch)+'_'+str(StepTime_buf)+'ms_'+ self.Time_text()
                self.textBroswerPrintRealTime('\n保存路径: '+ str(folder_path))  
                self.textBroswerPrintRealTime('CSV文件名: '+ str(csv_name))  
                
                header = ['DA_Hex','DA_Dec','Optical','Heater_P_V','Heater_P_I','Heater_N_V','Heater_N_I','Ppi_Power']        
                #行头数据存进CSV
                with open(self.filename, 'a', encoding='utf-8-sig', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(header)
            
                    csvfile.close()    
                
                self.RebackData_array_Power = [''] * SweepPoint
                self.TimeStart = self.Time_text()

                cmd_type = 1
                self.Sweep_QThread.Info_Copy( PowerSampling_cmd, cmd_type, Sweep_ch,  SweepPoint, StepTime, FirstPoint_Wait, self.Phase_Sweep, DaArray, self.RebackData_array_Power, self.filename, self.TimeStart) 
                self.Sweep_Start.setEnabled(False)
                self.Sweep_Stop.setEnabled(True)  
                self.Sweep_QThread.start()
            
    def Sweep_Stop_cb(self):
        self.Sweep_Stop_Flag = True
        self.Sweep_QThread.Loop_StopFlag = False

    def Loop_Done_cb(self,array_volt,array_power, steptime, point):
        self.Sweep_Start.setEnabled(True)
        self.Sweep_Stop.setEnabled(False)  
        if self.Sweep_Stop_Flag == False:
            self.polt_fig(array_volt,array_power,steptime, point)       
    def polt_fig(self, array_volt, array_power,steptime, point):
        fig = plt.figure()
        plt.figure(fig)
        
        # num = len(array_volt)
        # x = np.linspace(1, num, num)
        # plt.plot(x, array_power[0:num],'o',linestyle = '-')
        
        plt.plot(array_volt, array_power,'o',linestyle = '-')
        
        x = 0.1*(max(array_volt)-min(array_volt))+min(array_volt)
        y = 0.15*(max(array_power)-min(array_power))+min(array_power)
        ER = round(max(array_power)-min(array_power),2)
        plt.text(x,y,'point='+str(point)+'\nsteptime= '+str(steptime)+'ms\nER = '+str(ER))
        

        plt.title( 'P_arm_Volt vs Optical_dBm_'+str(self.MZ_Channel)+', steptime='+str(steptime)+'ms')
        plt.savefig(self.filename_polt +".png",dpi = 500)  
        # 显示图形
        plt.show()
     
    def GetPower_cb(self, flag = True):#read
        ch = self.PowerMeter_Ch_num
        port = self.PowerMeter_Port_num
        
        #需要同时配置好 当前单位
        command = ':FETC'+str(ch)+':CHAN'+str(port)+':POW?'
        Power = self.SendCmd_GetData(command)
        if Power == False:
            self.textBroswerPrintRealTime('读取光功率失败')
            print('读取光功率失败')
        else:
            try:
                Power = str(float(Power))[0:7]
            except:
                print('NA')
                Power = '99'
            if flag == True :
                self.textBroswerPrintRealTime('当前光功率:'+Power+self.PowerMeter_Unit)
            self.PowerMeter_Power.setText(Power)
            self.setting.setValue("setup_PowerMeter/Current_OpticalPower",Power)
            self.setting.setValue("setup_PowerMeter/Flag_OpticalPower_Change", True)
            sleep(0.001)
        return Power
    
    
    def textBroswerPrintRealTime(self, text, flag = [1,True,False] ):  # textBrowser实时打印信息
        self.LogPrint.emit(text, flag)   

    def Refresh_HeaterR(self):
        self.RefreshHeaterR_STM32.emit()


        
class QThread_SendCmd_SelPrint(QThread):
    
    LogPrint = pyqtSignal(str,list)
    Cmd_SetDAC = pyqtSignal(int, str, int, list)
    CmdTransfer_GetData = pyqtSignal(str, bool)
    UseExPD_GetAdcValue = pyqtSignal()
    Loop_Done = pyqtSignal(list,list, int, int)
    RefreshHeaterR_STM32 = pyqtSignal()  
    
    def __init__(self):
        super().__init__()#调用 父类中的__init__()方法
        self.print_info_all = [2, True, True]
        self.print_info_fast = [2, True, False]
        self.print_info_no = [2, False, False]

        self.HeaterR_Name_list = ['','XI_HeaterR_P','XI_HeaterR_N','XQ_HeaterR_P','XQ_HeaterR_N',
                                     'YI_HeaterR_P','YI_HeaterR_N','YQ_HeaterR_P','YQ_HeaterR_N',
                                     'XP_HeaterR_P','XP_HeaterR_N','YP_HeaterR_P','YP_HeaterR_N']  
        
        self.QTread_Run_flag = False
        self.Run_flag = False
        self.Loop_StopFlag = True
        self.Watting_Flag = False
        self.Loop_ReadPower_Flag = False
        
        self.cmd = ''
        self.flieName = ''
        self.RebackData_buf = ''
        self.Sweep_ch = ''
        self.CSV_data = ['']*9
        self.RebackData_array_Volt = None
        self.RebackData_array_Power = None
        
        self.Sweep_PointNum = 0
        
        self.TimeStart = ''
        self.TimeOver = ''         

        self.setting = QtCore.QSettings("./data/config_Board.ini", QtCore.QSettings.IniFormat)
        self.setting.setIniCodec("UTF-8")#设置格式
        self.STM32_ADC_VREF = float(self.setting.value("setup_Power/STM32_ADC_VREF"))

        # 设置CDM配置文件的路径 加载内容
        self.setting_CDM = QtCore.QSettings("./data/config_CDM.ini", QtCore.QSettings.IniFormat)
        self.setting_CDM .setIniCodec("UTF-8")#设置格式  


    def Info_Copy_Loop_ReadPower(self, cmd_buf, cmd_type_buf, Loop_ReadPower_Flag_buf,  \
                                    filename_buf = '', TimeStart_Flag=''):
        self.cmd = cmd_buf
        self.cmd_type = cmd_type_buf        
        self.Loop_ReadPower_Flag = Loop_ReadPower_Flag_buf
        self.flieName = filename_buf
        # self.RebackData_array_Power = RebackData_array_Power_buf
        self.TimeStart = TimeStart_Flag
        for i in range (9):
            self.CSV_data[i] = ''

    def Info_Copy(self, cmd_buf, cmd_type_buf, Sweep_ch_buf, Sweep_PointNum_buf, StepTime_buf, FirstPoint_Wait_buf, Phase_Sweep_buf, DA_Array, RebackData_array_Power_buf, \
                                    filename_buf = '', TimeStart_Flag=''):
        self.cmd = cmd_buf
        self.cmd_type = cmd_type_buf
        self.Sweep_ch = Sweep_ch_buf
        self.Sweep_PointNum = Sweep_PointNum_buf
        self.StepTime = StepTime_buf
        self.FirstPoint_Wait = FirstPoint_Wait_buf
        self.Phase_Sweep = Phase_Sweep_buf
        self.DAC_Array = DA_Array
        self.flieName = filename_buf
        self.RebackData_array_Volt = ['']*Sweep_PointNum_buf
        self.RebackData_array_Power = RebackData_array_Power_buf
        self.TimeStart = TimeStart_Flag
        
    def Time_text(self):
        return datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    def SentCmd_Only(self, cmd):
        #需要进行温度值的判断，形成设置温度的命令
        self.Watting_Flag = False
        self.CmdTransfer.emit(cmd, self.show_flag)
        self.Rx_Run_start()    
       
    def SentCmd_GetData(self, cmd):
        self.Watting_Flag = False
        self.CmdTransfer_GetData.emit(cmd, True)
        self.Rx_Run_start()
    def UseExPD_GetData(self):#PD档位+PD电流
        self.Watting_Flag = False
        self.UseExPD_GetAdcValue.emit()
        self.Rx_Run_start()        
        
    def RebackData_Save(self, data):
        #所有数据存进CSV
        self.RebackData_buf  = float(data)#返回的数据

        if self.cmd_type == 0:#记录光功率
            self.CSV_data[1] = float(data)
        else:#扫描调制曲线使用
            self.CSV_data[2] = float(data)
            #增加保存HeaterR 电压&电流，便于后续计算Ppi功率   
            self.Sweep_OnePointDone_SaveHeaterR_U_I_cb(self.CSV_data)#self.CSV_data[3:6]用来保存电压&电流

        with open(self.flieName, 'a', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(self.CSV_data)
            csvfile.close()        
        self.Watting_Flag = True        

    def Reback_AdcData_Save(self, flag, PD_Volt):
        #所有数据存进CSV
        self.RebackData_buf  = float(PD_Volt)/10000.0#返回的数据
        self.CSV_data[2] = float(PD_Volt)/10000.0#存到表格
        self.CSV_data[8] = flag

        #增加保存HeaterR 电压&电流，便于后续计算Ppi功率   
        self.Sweep_OnePointDone_SaveHeaterR_U_I_cb(self.CSV_data)#self.CSV_data[3:6]用来保存电压&电流
         
        with open(self.flieName, 'a', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(self.CSV_data)
            csvfile.close()        
                     
        self.Watting_Flag = True    


    def Sweep_OnePointDone_SaveHeaterR_U_I_cb(self,CSV_data):
        loc = (int(self.Sweep_ch)-1)*2#self.Sweep_ch默认从1开始,loc为了映射HeaterR_Name_list数组中的名称，方便读取对应通道的电压电流
        if self.setting_CDM.value('setup_HeaterR/Heater_Flag') ==  True:        
            for i in range (2):#P/N两个臂
                
                buf_Curr = self.setting_CDM.value('setup_HeaterR/'+str(self.HeaterR_Name_list[loc+i+1])+'_Curr')
                buf_Volt = self.setting_CDM.value('setup_HeaterR/'+str(self.HeaterR_Name_list[loc+i+1])+'_Volt')
                CSV_data[3+2*i]  = self.STM32_AdValue_calculate(self.Sweep_ch, str(buf_Curr) , 1)
                CSV_data[4+2*i]  = self.STM32_AdValue_calculate(self.Sweep_ch, str(buf_Volt) , 2)
            CSV_data[7] = CSV_data[3]*CSV_data[4] - CSV_data[5]*CSV_data[6]#计算Heater当前的Ppi功率
            self.setting_CDM.setValue('setup_HeaterR/Heater_Flag', False)
               
    def STM32_AdValue_calculate(self, ch, AdcValue, type=0):#type = 0:Power_Volt&ICC;type = 1:HeaterR_ICC;type = 2:HeaterR_Volt;
        volt = 0
        if type == 0:
            if ch ==1 or ch ==2 or ch ==5:
                volt = int(AdcValue)/4096.0*self.STM32_ADC_VREF/10.0*30
            elif  ch ==3 or ch ==4:
                volt = int(AdcValue)/4096.0*self.STM32_ADC_VREF/10*110/50.0/0.1*1000            
            elif  ch ==6:
                volt = int(AdcValue)/4096*self.STM32_ADC_VREF*3-5.039
        elif  type == 1:
            volt = int(AdcValue)/4096*self.STM32_ADC_VREF/20/2*1000
        elif  type == 2:
            # volt = int(AdcValue)/4096*self.STM32_ADC_VREF/10*30
            volt = int(AdcValue)/4096*self.STM32_ADC_VREF/1*4.3
        return  float(volt)
    
    def Loop_Over(self):
        self.Loop_StopFlag == False
    
    def textBroswerPrintRealTime(self, cmd, ShowFlag=[0, True, False]):
        self.LogPrint.emit(cmd, ShowFlag)
    def Time_calculate(self, TimeStart, TimeOver):
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
        # print(f"时间差（秒）: {total_seconds}")   
        self.textBroswerPrintRealTime(f"Lock时间差(秒): {total_seconds}")  
    def Rx_Run_start(self):#小循环启动 
        self.Run_flag = True          
    def Rx_Run_Stop(self): #小循环结束
        self.Run_flag = False
    def Stop(self): #大循环结束
        self.QTread_Run_flag = False

    #子线程在调用start()后，就一直在run()中循环，一旦里面的while结束则子线程也就结束了
    #只有子线程一直存在，才能随时 接收来自主进程的信息 或者 向外发送信息
    #也只有在run()中，进行 信息的等待、接收、处理 或者 给主程序回送消息，GUI才不卡顿    
    def run(self): 
        i = 0
        self.QTread_Run_flag = True
        self.Run_flag = True
        if self.cmd_type == 0:#cmd_type = 0  只记录光功率
            try:
                #进入轮询：1.等待RX回复 指令执行完毕，回复 'AFAF'； 或者 等待RX回复 指令所需回读的数据
                while self.QTread_Run_flag:
                    if self.cmd != '':
                        self.SentCmd_GetData(self.cmd)#读取 光功率   
                        self.CSV_data[0] = str(self.Time_text())
                        sleep(1)
                    else:

                        pass  
                        
                    while self.Run_flag == True:#进入小循环等待Rx回复
                        self.textBroswerPrintRealTime(str(i)+', Power: '+str(self.RebackData_buf)[0:6]+'dBm, '+self.Time_text())
                        i = i+1
                        #循环结束
                        if self.Loop_ReadPower_Flag == False:
                            self.TimeOver = self.Time_text()
                            self.textBroswerPrintRealTime('Loop结束,   '+self.TimeOver)
                            self.Rx_Run_Stop()
                            self.Stop()#loop结束，子线程结束
                        #当此次 获取数据结束
                        self.Rx_Run_Stop()#小循环结束，启动新一次Cmd发送
            except:

                self.textBroswerPrintRealTime('print(QThread) 失败')

        else:#cmd_type = 1  记录调制曲线
            if i == 0:#第一个点，做长延时
                #下发Heater通道的DAC
                self.Cmd_SetDAC.emit(self.Sweep_ch,self.DAC_Array[i], 0, self.print_info_no)#参数channel, DA_hex, Action_Num = 0, show_flag = [2,True,True]  
                if self.Sweep_ch == 5 or self.Sweep_ch == 6:#Phase扫描 需要拉偏IQ路
                        self.Cmd_SetDAC.emit(self.Phase_Sweep[0],self.Phase_Sweep[2], 0, self.print_info_no)
                        self.Cmd_SetDAC.emit(self.Phase_Sweep[1],self.Phase_Sweep[3], 0, self.print_info_no)
                self.textBroswerPrintRealTime('\nFirst Point_Wait_Time:'+str(self.FirstPoint_Wait)+'s\n')
                sleep(int(self.FirstPoint_Wait)) 
                self.TimeStart = self.Time_text()
            try:
                #进入轮询：1.等待RX回复 指令执行完毕，回复 'AFAF'； 或者 等待RX回复 指令所需回读的数据
                while self.QTread_Run_flag:
                    #发送指令，自动判断 串口是否发送成功、校验RX是否接收到正确的指令
                    #下发Heater通道的DAC
                    self.Cmd_SetDAC.emit(self.Sweep_ch,self.DAC_Array[i], 0, self.print_info_no)#参数channel, DA_hex, Action_Num = 0, show_flag = [2,True,True]
                    self.CSV_data[0] = self.DAC_Array[i]
                    self.CSV_data[1] = int(self.DAC_Array[i],16)/4096*3.3*2
                    self.RebackData_array_Volt[i] =  self.CSV_data[1]
                    
                    self.RefreshHeaterR_STM32.emit()#触发信号,读取Heater 电压/电流
                    sleep(self.StepTime) 
                    if self.cmd != '':
                        self.SentCmd_GetData(self.cmd)#读取 光功率   
                    else:
                        self.UseExPD_GetData()#使用EXPD 读取光功率
                        sleep(0.05)
                        pass  
                        
                    while self.Run_flag == True:#进入小循环等待Rx回复
                        
                        while self.Watting_Flag == False:
                            sleep(0.002) 
                        self.RebackData_array_Power[i]= self.RebackData_buf#记录数据
                        if self.cmd != '':
                            self.textBroswerPrintRealTime(str(i)+', '+str(self.DAC_Array[i])+', Power: '+str(self.RebackData_buf)[0:6]+'dBm')
                        else:
                            self.textBroswerPrintRealTime(str(i)+', '+str(self.DAC_Array[i])+', Power_Curr: '+str(self.RebackData_buf)[0:6]+'mA')
                        i = i+1
                        #循环结束
                        if self.Loop_StopFlag == False or i == self.Sweep_PointNum:
                            self.TimeOver = self.Time_text()
                            self.textBroswerPrintRealTime('Loop结束,   '+self.TimeOver)
                            self.Time_calculate(self.TimeStart,self.TimeOver)
                            
                            self.Cmd_SetDAC.emit(self.Sweep_ch,self.DAC_Array[0], 0, self.print_info_no)#恢复初始值
                            
                            
                            if self.Sweep_ch == 5 or self.Sweep_ch == 6:#Phase扫描 结束，恢复IQ路
                                self.Cmd_SetDAC.emit(self.Phase_Sweep[0],self.Phase_Sweep[4], 0, self.print_info_no)
                                self.Cmd_SetDAC.emit(self.Phase_Sweep[1],self.Phase_Sweep[5], 0, self.print_info_no)
                            #如果 光功率计记录调制曲线，    RebackData_array_Power是指dBm
                            #如果 EXPD记录调制曲线，    RebackData_array_Power是指光电流
                            self.Loop_Done.emit(self.RebackData_array_Volt, self.RebackData_array_Power, int(self.StepTime*1000),int(self.Sweep_PointNum))
        
                            self.Rx_Run_Stop()
                            self.Stop()#loop结束，子线程结束
                        #当此次 获取数据结束
                        self.Rx_Run_Stop()#小循环结束，启动新一次Cmd发送
            except:

                self.textBroswerPrintRealTime('print(QThread) 失败')
            
                    

if __name__ == '__main__':
    # QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    app = QtWidgets.QApplication(sys.argv)    #1.创建一个应用程序的对象
    Form = QtWidgets.QWidget()
    myWindow = Sweep_ModulatinCurve()
    myWindow.show()

    #3.应用程序的执行 进入消息循环
    sys.exit(app.exec_())

