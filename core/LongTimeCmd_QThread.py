
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal,QThread
import matplotlib.pyplot as plt
import numpy as np 
from time import sleep
import sys,os,re,datetime,csv

sys.path.append(os.getcwd())


class SendCmd_SelPrint_Waitting_CheckDone_cb(QThread):
    
    # Update_signal = pyqtSignal(str)#自定义信号：串口需启动发送的signal，用于接收来自主函数的Tx指令
    # Finish_signal = pyqtSignal()

    Uart_TxCmd_Flag= pyqtSignal(str, int, list)
    
    Uart_TxFinish_Flag = pyqtSignal(str, bool, list)#串口 tx信息、发送成功标志位、是否打印标志位
    Uart_RebackSignal = pyqtSignal( int, list)#串口回传的信息：个数 & 数据接收完成的标志 & 是否由线程触发->打印信息
    Uart_RxCheckTx_Signal = pyqtSignal(str, str, list)#校验 Rx是否接收到正确的TxCmd
    Uart_Reback_QThreadFinish_Signal = pyqtSignal( int, list)#串口回传的信息：个数 & 数据接收完成的标志 & 是否由线程触发->打印信息

    Refresh_6ch_HeaterDA_Flag = pyqtSignal( )
    Refresh_IQ_Aligemnt_Info = pyqtSignal( )
    Record_Plot_En = pyqtSignal( bool)
    COM_Settings = pyqtSignal( bool)#长数据读取，修改串口等待时间
    FindPoint_OverTime = pyqtSignal( str)
    Trigger_Uart_StartFlag = pyqtSignal(bool)
    Trigger_Uart_StoptFlag = pyqtSignal( )

    Trigger_Uart_ClearBuffer = pyqtSignal()
    Trigger_LockStop = pyqtSignal(int)#停止锁定，同时传输结束时的锁定次数
    Trigger_LockCycle_show = pyqtSignal(int)
    Trigger_LockInfo_show = pyqtSignal(list)
    
    Trigger_Refresh_HeaterR = pyqtSignal()
    Trigger_Calibrate_X_IQ_Loop = pyqtSignal()
    Trigger_Calibrate_Y_IQ_Loop = pyqtSignal()
    Trigger_Calibrate_XP_Loop = pyqtSignal()
    Trigger_Calibrate_YP_Loop = pyqtSignal()
    Trigger_Call_PowerMeter = pyqtSignal(bool)
    
    
    def __init__(self, LogPrint_flag, Rx_Array_flag):#cmd_flag, Action_Text_Flag, Action_Num_flag, Data_show_Flag, Rx_Array_Flag
        super().__init__()#调用 父类中的__init__()方法

        self.QTread_Run_flag = False
        self.Run_flag = False
        self.Record_Plot_Flag = True
        self.DoLocking_Flag = False
        self.LockCycle_Target = 1
        self.LockCycle_Err = 0
        self.Flag_Clear =  False
        self.print_info_all = [2, True, True]
        self.print_info_fast = [2, True, False]
        self.print_info_no = [2, False, False]    
        
        self.Action_Num_Normal = 0
        self.Action_Num_FindPoint           = 1000#FindPoint
        self.Action_Num_PhAgainFindPoint    = 1001#PhaseAgain_FindPoint 
        self.Action_Num_IQAlignment         = 1002#IQAlignment
        self.Action_Num_IQLock              = 1003#IQLock
        
        self.Action_Num_FindPointRecrodSave = 1021# FindPoint saveData
        self.Action_Num_IQLock_Curve        = 1022# IQLock_Curve SAVE+POLT
        self.Action_Num_XY_Lock             = 1030# XY LOCK
        self.Action_Num_LockCalibration     = 1031# Deri_Calibration
        
        self.Amp = 0
        self.Amp_Step = 0
        self.CalibrateLocking_cycle_buf = 0
        
        self.cmd = ''
        self.Action_Text = ''
        self.Action_Num = ''
        self.show_flag = ['']*3
        self.Rx_Array = Rx_Array_flag
        self.LogPrint = LogPrint_flag
        
        self.GUI_Refresh_flag = False
        self.FlieName = ''
        self.error_flag = 0
        
        self.Rx_Array_buf = ['']*30
        
        self.HeaterR_Name_list = ['','XI_HeaterR_P','XI_HeaterR_N','XQ_HeaterR_P','XQ_HeaterR_N',
                                'YI_HeaterR_P','YI_HeaterR_N','YQ_HeaterR_P','YQ_HeaterR_N',
                                'XP_HeaterR_P','XP_HeaterR_N','YP_HeaterR_P','YP_HeaterR_N']             
        
        # 设置串口配置文件的路径 加载内容
        self.setting = QtCore.QSettings("./data/config_Board.ini", QtCore.QSettings.IniFormat)
        self.setting.setIniCodec("UTF-8")#设置格式
        # 设置CDM配置文件的路径 加载内容
        self.setting_CDM = QtCore.QSettings("./data/config_CDM.ini", QtCore.QSettings.IniFormat)
        self.setting_CDM .setIniCodec("UTF-8")#设置格式
        
        self.STM32_ADC_VREF = float(self.setting.value("setup_Power/STM32_ADC_VREF"))

        self.SerialPortB_COM = self.setting.value("setup_SerialPortB/SerialPortB_COM")

        self.Uart_TxFinish_Flag.connect(self.Uart_TxFinish_Check)
        self.Uart_RxCheckTx_Signal.connect(self.RxReceiveTxCmd_Check) 
        
        self.Uart_Reback_QThreadFinish_Signal.connect(self.RxDataRecord_SeLAction_cb)
        self.Record_Plot_En.connect(self.FindPoint_Record_Plot)
        
    def Info_Copy(self, cmd_flag, Action_Text_Flag, Action_Num_Flag, Data_show_Flag, Rx_Array_buf1, FindPoint_Record_length_buf, 
                  DoLocking_Flag_buf,  Filename = '', FileName_HeaterR = '', CalibrateLocking_Flag_buf = '', record_Power_buf = '', Amp_buf = '', Amp_Step_buf = ''):
        self.cmd = cmd_flag
        self.Action_Text = Action_Text_Flag
        self.Action_Num = Action_Num_Flag
        self.DoLocking_Flag = DoLocking_Flag_buf
        self.CalibrateLocking_Flag = CalibrateLocking_Flag_buf
        self.Amp = Amp_buf
        self.Amp_Step = Amp_Step_buf
        self.Array_For_Calibrate = record_Power_buf
        self.show_flag[0] = Data_show_Flag[0]
        self.show_flag[1] = Data_show_Flag[1]
        self.show_flag[2] = Data_show_Flag[2]

        self.Rx_Array = Rx_Array_buf1     
        self.FlieName = Filename
        self.FileName_HeaterR = FileName_HeaterR
        self.FindPoint_Record_length = FindPoint_Record_length_buf
        
        
    def FindPoint_Record_Plot(self, Flag): 
        self.Record_Plot_Flag  = Flag
            
    def Time_text(self):
        return datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S")        
    def Time_record(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #实时打印信息, 需要窗口之间传输信息
    def textBroswerPrintRealTime(self, text = '', show_flag = [2,True,False]):  
        self.LogPrint.emit(text, show_flag)
        
    #串口TX相关函数
    def Uart_TxFinish_Check(self, cmd, TxFlag, show_flag):
        #Tx发送成功，判断 是否成功发送
        if show_flag[2] == True:            
            if TxFlag == True:
                text1 = str(self.SerialPortB_COM)+' SendSucceed/'+str(self.SerialPortB_COM)+'发送成功, '
            else:
                text1 = str(self.SerialPortB_COM)+' SendFaild/'+str(self.SerialPortB_COM)+'发送失败, '           
            self.textBroswerPrintRealTime(text1+self.Time_record())     
    def RxReceiveTxCmd_Check(self, text, text1, show_flag):
        #Rx接收到cmd，判断 是否接收到正确的指令
        if show_flag[2] == True:
            if text == text1:
                text2 = 'FW接收到正确的TxCmd: '+ text1
            else:
                text2 = 'FW接收到错误的TxCmd: '+ text1       
            self.textBroswerPrintRealTime(text2)   
    def SendHexCmd(self, cmd_Raw,  Action='', Action_Num=999, show_flag=[2,True,True]):
        #发送TxCmd：传输指令、指令的名称、指令回调的函数ID、打印TxRX信息的标志位
        #注意：RxDataNum > 999，则表示进行占用长时间的写操作
        for i in range (30):#清空数组
            self.Rx_Array[i] = ''  
            
        cmd = re.sub(r"\s+", "", cmd_Raw).upper()  # 去除空格
        if show_flag[1] == True and Action_Num != self.Action_Num_XY_Lock:
            self.textBroswerPrintRealTime(Action)
        if show_flag[2] == True:
            self.textBroswerPrintRealTime(cmd)                
        self.Uart_TxCmd_Flag.emit(cmd, Action_Num, show_flag)#触发自定义信号,启动Uart_Tx并判断是否成功发送,1:返回信息进入数据进行保存
    #处理返回的数据，获取 操作的完成状态
    def CheckDone(self, RxData, action, show_flag):
        try:
            text = str(action).split('/')#有可能出错
            if RxData[ show_flag[0]-1 ][-4:] == 'AFAF':
                text1 = str(text[0]) + " Done/"+ str(text[1])+" 执行完成"
            else:
                text1 = str(text[0]) + " Fail/"+ str(text[1])+" 执行失败"
        except:
            if RxData[ show_flag[0]-1 ][-4:] == 'AFAF':
                text1 = action + " Done.  "
            else:
                text1 = action + " Fail.  "
            
        if  show_flag[1] == True:       
            self.textBroswerPrintRealTime(text1)    
            self.textBroswerPrintRealTime(self.Time_record())           
            self.textBroswerPrintRealTime('')
                    
    #接收 Rx回复的信息，#传递 指令回调ID、选择 打印信息的标志位
    def RxDataRecord_SeLAction_cb(self, Action_Num, show_flag):
        #关闭QThread子线程内的小循环
        self.Rx_Run_Stop()  
        #记录 Rx数据和回调函数的ID
        self.Action_Num_ID = Action_Num  
        for i in range (show_flag[0]):
                self.Rx_Array_buf[i] = self.Rx_Array[i]

        match self.Action_Num_ID:
            case self.Action_Num_FindPoint:
                self.RxData_Print_cb( show_flag, self.Rx_Array_buf)
                self.FindPoint_Done_cb()
            case self.Action_Num_PhAgainFindPoint:
                self.PhaseAgain_Findpoint_Done_cb()
            case self.Action_Num_IQAlignment:
                self.EXPD_IQLock_Alignemet_Done_cb()
            case self.Action_Num_IQLock:
                self.IQLockPoint_Done_cb()      
            case self.Action_Num_FindPointRecrodSave:
                self.FindPoint_RecordSave_Done_cb()
            case self.Action_Num_IQLock_Curve:# 1022 IQLock_Curve SAVE+POLT
                # self.FindPoint_RecordSave_Done_cb()  
                1           
            case self.Action_Num_XY_Lock:
                self.XYLocking_OneCycleDone_cb()                
            case self.Action_Num_LockCalibration:
                self.LockCalibration_Done_cb()                    
            case default:
                self.textBroswerPrintRealTime('执行完成,无回调函数')
    def RxData_Print_cb(self, show_flag, array):
        #打印Rx接收到的所有数据
        if show_flag[2] == True:
            self.textBroswerPrintRealTime('RebackData '+str(show_flag[0])+' Words:')
            for i in range (show_flag[0]):
                    self.textBroswerPrintRealTime(array[i])       
   

    def FindPoint_Done_cb(self):#找点结束 刷新显示
        self.Action_Text = 'CDM Find WorkingPoint/CDM NNQ找点'
        self.CheckDone(self.Rx_Array, self.Action_Text, self.show_flag)
        self.FindPoint_OverTime.emit(self.Time_text())#发送结束时间
        self.Refresh_6ch_HeaterDA_Flag.emit()
        self.textBroswerPrintRealTime('刷新HeaterDA显示', self.show_flag)
    def IQLockPoint_Done_cb(self):

        self.Action_Text = '@EX_PD, IQ Locking'
        self.CheckDone(self.Rx_Array_buf, self.Action_Text, self.show_flag)  

        self.Refresh_6ch_HeaterDA_Flag.emit()
        self.textBroswerPrintRealTime('刷新HeaterDA显示', self.show_flag)        
    def EXPD_IQLock_Alignemet_Done_cb(self):#IQ锁定 相位对齐              

        self.Action_Text = '@EXPD, IQLock_Alignemet'
        self.CheckDone(self.Rx_Array_buf, self.Action_Text, self.show_flag)          
        # 执行完成后,更新校准的信息
        self.Refresh_IQ_Aligemnt_Info.emit()
    
    def FindPoint_RecordSave_Done_cb(self):
        
        self.FindPointRecord_SaveCSV_Polt_cb()
        sleep(0.002)
        self.Action_Text = 'FindPoint_Record_Save'
        self.CheckDone(self.Rx_Array_buf, self.Action_Text, self.show_flag)    
        
        self.COM_Settings.emit(True)    
        sleep(0.002)   
    def FindPointRecord_SaveCSV_Polt_cb(self): #放在子线程运行  处理数据和画图        

        # self.FindPointRecord_Save_Thread.Stop()#子线程大循环结束

        CDM_SN = self.setting_CDM.value("setup/CDM_SN")
        CDM_T0 = self.setting_CDM.value("setup/T0")
        CDM_WL0 = self.setting_CDM.value("setup/WL0")        

        folder_path = './log/' + CDM_SN + '/' + CDM_SN +'_'+ str(CDM_T0) +'c_'+ str(CDM_WL0)
        # print(folder_path)
        if not os.path.exists(folder_path):

            os.makedirs(folder_path)
            # print("文件夹创建成功")
            # self.textBroswerPrintRealTime("文件夹创建成功")
        else:
            # print("文件夹已存在")
            # self.textBroswerPrintRealTime("文件夹已存在")
            None
        
        # csv文件名称
        filename = './log/' + CDM_SN + '/' + CDM_SN +'_'+ str(CDM_T0) +'c_'+ str(CDM_WL0) + '/' + CDM_SN +'_'+ str(CDM_T0) +'c_'+ str(CDM_WL0) + '_FindPoint_Record'+'_'+ self.Time_text()+'.csv' 
        self.textBroswerPrintRealTime('\nCSV创建完成:\n'+'filename: ' + str(filename)) 
        
        filename1 = './log/' + CDM_SN + '/' + CDM_SN +'_'+ str(CDM_T0) +'c_'+ str(CDM_WL0) + '/' + CDM_SN +'_'+ str(CDM_T0) +'c_'+ str(CDM_WL0) +'_FindPoint_Record'+'_'+ self.Time_text()
        #3种数组长度  26/20/30
        # length 顺序 I、Q、P、P_again
        length = self.FindPoint_Record_length
        length_flg = [0, 1, 0, 1, 0, 1, 0, 1]#顺序 （DA&data）*4   
        
        # self.Rx_Array_buf[0]:原指令
        # self.Rx_Array_buf[1~8]:XPOL找点数据
        # self.Rx_Array_buf[9~16]:YPOL找点数据
        # self.Rx_Array_buf[17]:FindPoit NNQ
        # self.Rx_Array_buf[18]:LockPoint NNQ
        # self.Rx_Array_buf[19]:结束 指令
        
        array_Offset= 1       
        #X和Y都为8*30的二维数组，record存放顺序 I、Q、P、P_again
        array_X =  [[0] * length for _ in range(8)]#二维矩阵
        array_Y =  [[0] * length for _ in range(8)]#二维矩阵        

        self.textBroswerPrintRealTime("数据处理中...")

        for i in range(8):
            self.LongData_process(self.Rx_Array_buf[array_Offset+i], length, array_X[i], length_flg[i])#处理数据
            
        header = ['XI_DA','XI_ScanNull_CurveValue','XQ_DA','XQ_ScanNull_CurveValue','XP_DA','XP_ScanQuad_CurveValue','XP_ScanAgain_Da','XP_ScanAgain_Quad_CurveValue']        
        #所有数据存进CSV
        data = list(zip(*array_X))  # 行列转换
        with open(filename, 'a', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)
            for i in data:#  write in CSV
                writer.writerow(i)
            csvfile.close()    
        
        #Y POL.
        for i in range(8):
            self.LongData_process(self.Rx_Array_buf[array_Offset+8+i],length, array_Y[i], length_flg[i])#一次性读取  WordNum*6个字节的长数据
            
        header = ['YI_DA','YI_ScanNull_CurveValue','YQ_DA','YQ_ScanNull_CurveValue','YP_DA','YP_ScanQuad_CurveValue','YP_ScanAgain_Da','YP_ScanAgain_Quad_CurveValue']        
        #所有数据存进CSV
        data = list(zip(*array_Y))  # 行列转换
        # write in DAdata   
        with open(filename, 'a', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)
            for i in data:#  write in CSV
                writer.writerow(i)
            csvfile.close()    

        #FindPoint Info
        array_FindPointInfo_buf =  [0] * 16
        self.LongData_process(self.Rx_Array_buf[array_Offset+8+8+0], 16, array_FindPointInfo_buf, 0)#一次性读取  WordNum*6个字节的长数据
        header = ['XI_NullDA','XQ_NullDA','XP_QuadDA','YI_NullDA','YQ_NullDA','YP_QuadDA',
                    'XI_CPoint','XQ_CPoint','XP_CPoint','YI_CPoint','YQ_CPoint','YP_CPoint',
                    'XI_MAXDA','XQ_MAXDA','YI_MAXDA','YQ_MAXDA']   
        array_FindPointInfo =  [[0] * 1 for _ in range(16)]#二维矩阵 
        for i in range(16):    
            array_FindPointInfo[i][0] = array_FindPointInfo_buf[i]

        #所有数据存进CSV
        data = list(zip(*array_FindPointInfo))  # 行列转换
        # write in DAdata   
        with open(filename, 'a', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)
            for i in data:#  write in CSV
                writer.writerow(i)
            csvfile.close()    

        #LockPoint Info    
        array_LockPointInfo_buf =  [0] * 6
        self.LongData_process(self.Rx_Array_buf[array_Offset+8+8+1], 6, array_LockPointInfo_buf, 0)#一次性读取  WordNum*6个字节的长数据
        header = ['XI_NullDA','XQ_NullDA','XP_QuadDA','YI_NullDA','YQ_NullDA','YP_QuadDA','LockPoint Info']   
        array_LockPointInfo =  [[0] * 1 for _ in range(6)]#二维矩阵 
        for i in range(6):    
            array_LockPointInfo[i][0] = array_LockPointInfo_buf[i]
        #所有数据存进CSV
        data = list(zip(*array_LockPointInfo))  # 行列转换
        # write in DAdata   
        with open(filename, 'a', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)
            for i in data:#  write in CSV
                writer.writerow(i)
            csvfile.close()   
        self.textBroswerPrintRealTime("FindPoint_DataRecord Done./找点数据 保存完成！")
        
        
        
        if self.Record_Plot_Flag == True:
            
            self.textBroswerPrintRealTime('数据 画图中..')
            
            fig = plt.figure(figsize=(12,6))
            plt.figure(fig)
            t = 0
            fig_title_X = ['XI','XQ','XP','XP_again']
            for i in range(4):
                # 创建子图
                plt.subplot(2, 4, i+1)
                # 绘制图形
                x = np.linspace(1,length,length)
                # print(x)
                # print( array_X[2*i+1])  
                plt.plot(x, array_X[2*i+1],'o',linestyle = '-')
                # 设置第一个子图的标题
                if i !=2:
                    t = i
                    if i ==3:#只显示Phase_again
                        t=2
                    plt.title( fig_title_X[i]+", "+str(int(array_FindPointInfo[6+t][0],16)) )
                else:
                    plt.title( fig_title_X[i] )
            t = 0        
            fig_title_Y = ['YI','YQ','YP','YP_again']
            for i in range(4):
                # 创建子图
                plt.subplot(2, 4, i+5)
                # 绘制图形
                x = np.linspace(1,length,length)
                # print(x)
                # print( array_X[2*i+1])  
                plt.plot(x, array_Y[2*i+1],'o',linestyle = '-')
                # 设置第一个子图的标题
                if i !=2:
                    t = i
                    if i ==3:#只显示Phase_again
                        t=2
                    plt.title(fig_title_Y[i]+", "+str(int(array_FindPointInfo[9+t][0],16)))
                else:
                    plt.title( fig_title_X[i] )

            # 调整子图之间的间距
            plt.tight_layout()
            
            plt.savefig(filename1+".png",dpi = 300)  
            # 显示图形
            plt.show()
            
        self.textBroswerPrintRealTime('画图 已完成')
        
        # #保存温度
        # data1 =  [[0] * 4 for _ in range(1)]#二维矩阵
        # data1[0][0] = "CDM_Tempreture:"
        # data1[0][1] = self.setting_CDM.value("setup/CDM_Temperature")#
        # data1[0][2] = "DRV_Tempreture:"
        # data1[0][3] = self.setting_CDM.value("setup/DRV_Temperature")#
        # data = list(zip(*data1))  # 行列转换
        #     #write in DAdata
        # with open(filename, 'a', encoding='utf-8-sig', newline='') as csvfile:
        #     writer = csv.writer(csvfile)
        #     # writer.writerow(header)
        #     for i in data:#  write in CSV
        #         writer.writerow(i)
        #     csvfile.close()                            
    def LongData_process(self, RxArray, cycle, array, flag):#处理数据即可  WordNum*6个字节的长数据
        
            if flag == 0:  # 读取DA
                for cycle_buf in range(cycle):
                    array[cycle_buf]= '0x'+ RxArray[cycle_buf*12+8:cycle_buf*12+12]
            if flag == 1:#读取Scan null data、Scan null CurveValue
                for cycle_buf in range(cycle):
                    try:
                        if RxArray[(cycle_buf*12+7):(cycle_buf*12+8)]== '0':
                            array[cycle_buf] = int(RxArray[(cycle_buf*12+8):(cycle_buf*12+12)],16)/10000.0
                        else:
                            array[cycle_buf] = 0-int(RxArray[(cycle_buf*12+8):(cycle_buf*12+12)],16)/10000.0
                    except:
                        print(RxArray, '1')
                        self.textBroswerPrintRealTime('数据出错')
                     
    def PhaseAgain_Findpoint_Done_cb(self):#Phase完成再次找点    
        
        self.Action_Text = 'XP&YP Again_Findpoint'
        self.CheckDone(self.Rx_Array_buf, self.Action_Text, self.show_flag)          
        # 执行完成后,更新校准的信息
        self.Refresh_6ch_HeaterDA_Flag.emit()
        self.textBroswerPrintRealTime('刷新HeaterDA显示',self.show_flag)  
    
    def XYLocking_OneCycleDone_cb(self):#每完成一次锁定    
        
        self.Action_Text = 'All_Ch_locking '
        self.CheckDone(self.Rx_Array_buf, self.Action_Text, self.show_flag)   
        self.Trigger_LockInfo_show.emit(self.Rx_Array_buf)
        
        if self.CalibrateLocking_Flag == False:#常规情况下，锁定
            # 执行完成后,更新校准的信息并保存数据
            if self.setting_CDM.value('setup/LockRecord_EnSave') ==  True:
                self.XYLocking_OneCycleDone_SaveData_cb(self.Rx_Array_buf)
                self.XYLocking_OneCycleDone_SaveHeaterR_cb()
                
        else:#校准情况下，锁定
            #当锁定完成一次 记录一次上报的光功率值
            if self.setting.value("setup_PowerMeter/Flag_OpticalPower_Change")  == True:
                self.Array_For_Calibrate[self.CalibrateLocking_cycle_buf] = self.setting.value("setup_PowerMeter/Current_OpticalPower")  
            else:#光功率每更新，则该数值为空
                self.Array_For_Calibrate[self.CalibrateLocking_cycle_buf] = 'NA'
            self.setting.setValue("setup_PowerMeter/Flag_OpticalPower_Change", False)    
            
    def XYLocking_OneCycleDone_SaveData_cb(self, RxArray):
        try:
            array = ['']*12
            # 处理DA
            for cycle_buf in range(6):
                try:
                    array[cycle_buf]= int( RxArray[1][cycle_buf*12+8:cycle_buf*12+12],16 )
                    sleep(0.01)
                except:
                    print(RxArray, '2')
                    self.textBroswerPrintRealTime('数据出错')  

            #处理导数
            for cycle_buf in range(6):
                try:
                    Value = RxArray[2][cycle_buf*12+8:cycle_buf*12+12]
                    #取hex值的最高位判断导数的正负
                    flag = int( int(Value,16)>>15 )
                    if flag == 0:
                        array[cycle_buf+6] = str(float(round( int(Value, 16)/100.0, 5)))[:4]
                    elif flag ==1:
                        array[cycle_buf+6] = str(float(round( 0 - (int(Value,16) & 0x7FFF)/100.0, 5)))[:5]   
                except:
                    print(RxArray, '3')
                    self.textBroswerPrintRealTime('数据出错')    
            #对数组的数据进行重新排列，使其符合 保存的格式
            array_buf = ['']*(12+3)
            
            for i in range(6):
                    array_buf[i*2] = array[i]
                    array_buf[i*2+1] = array[i+6] 
                    
            array_buf[12] = str(self.Time_text())#增加时间戳
            array_buf[13] = int( RxArray[3][6*12+8:6*12+12],16 )
            array_buf[14] = int( RxArray[3][7*12+8:7*12+12],16 )
            volt_PD = array_buf[14]/65535*2.5/10*15.1 
            
            self.setting_CDM.setValue("LockPoint/PD_Res_flag",array_buf[13])
            self.setting_CDM.setValue("LockPoint/LockPoint_EXPD_ADC_Value",round(volt_PD,7))        
            array_buf[14] = round(volt_PD,7)
        except:
            self.textBroswerPrintRealTime('XYLocking_OneCycleDone_SaveData_cb error')
        
        #所有数据存进CSV
        data = array_buf
        with open(self.FlieName , 'a', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(data)
            csvfile.close()    
 
    def XYLocking_OneCycleDone_SaveHeaterR_cb(self):
        R_buf = ['']*(12+12+12+6+2)       
        if self.setting_CDM.value('setup_HeaterR/Heater_Flag') ==  True:       
            for i in range (12):
                R_buf[i]  = self.setting_CDM.value('setup_HeaterR/'+str(self.HeaterR_Name_list[i+1]))    
                buf_Curr  = self.setting_CDM.value('setup_HeaterR/'+str(self.HeaterR_Name_list[i+1])+'_Curr')
                buf_Volt  = self.setting_CDM.value('setup_HeaterR/'+str(self.HeaterR_Name_list[i+1])+'_Volt')
                R_buf[12+i]  = self.STM32_AdValue_calculate(str(buf_Curr) , 1)
                R_buf[24+i]  = self.STM32_AdValue_calculate(str(buf_Volt) , 2)  
                if i%2 == 1:
                    R_buf[36+int(i/2)] = float(R_buf[12+i-1])*float(R_buf[24+i-1]) - float(R_buf[12+i])*float(R_buf[24+i])#计算Heater当前的Ppi功率   
            self.setting_CDM.setValue('setup_HeaterR/Heater_Flag', False) 
            
        if self.setting_CDM.value('setup/DRV_Temperature_Flag') ==  True and self.setting_CDM.value('setup/DRV_Temperature_SaveFlag') ==  True: 
            R_buf[12+12+12+6] = self.setting_CDM.value('setup/DRV_Temperature')
            self.setting_CDM.setValue('setup/DRV_Temperature_Flag', False)
        else:
            R_buf[12+12+12+6] = '-7777'
        R_buf[12+12+12+6+1] = self.Time_text()
            
        if R_buf[0] != '':
            #所有数据存进CSV
            data = R_buf
            with open(self.FileName_HeaterR , 'a', encoding='utf-8-sig', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(data)
                csvfile.close()    
    def STM32_AdValue_calculate(self, AdcValue, type=0):#type = 0:Power_Volt&ICC;type = 1:HeaterR_ICC;type = 2:HeaterR_Volt;
        volt = 0
        if type == 0:
            None
        elif  type == 1:
            volt = int(AdcValue)/4096*self.STM32_ADC_VREF/20/2*1000
        elif  type == 2:
            # volt = int(AdcValue)/4096*self.STM32_ADC_VREF/10*30
            volt = int(AdcValue)/4096*self.STM32_ADC_VREF/1*4.3
        return  float(volt)
    
    def LockCalibration_Done_cb(self):

        cmd_buf = re.sub(r"\s+", "", self.cmd).upper()
        #处理数据，并保存CSV
        self.LockCalibration_SaveCSV_Polt_cb(cmd_buf)
        sleep(0.002)
        
        self.Action_Text = 'LockCalibration'
        self.CheckDone(self.Rx_Array_buf, self.Action_Text, self.show_flag)    
    def LockCalibration_SaveCSV_Polt_cb(self,cmd_buf):
        
        CDM_SN = self.setting_CDM.value("setup/CDM_SN")
        CDM_T0 = self.setting_CDM.value("setup/T0")
        CDM_WL0 = self.setting_CDM.value("setup/WL0")        

        folder_path = './log/' + CDM_SN + '/' + CDM_SN +'_'+ str(CDM_T0) +'c_'+ str(CDM_WL0)

        if not os.path.exists(folder_path):

            os.makedirs(folder_path)
            # print("文件夹创建成功")
            # self.textBroswerPrintRealTime("文件夹创建成功")
        else:
            # print("文件夹已存在")
            # self.textBroswerPrintRealTime("文件夹已存在")
            None
        
        #数组长度
        length = 9
        length_flg = [0, 1]#顺序 （DA&data）*4
        ch = 0
        name=''
        header = ''

        if cmd_buf[4:6] =='FB':
            
            match cmd_buf[6:8]:
                case '03':
                    ch = 5
                case '04':
                    ch = 6
            
        elif cmd_buf[4:6] =='FC':
            match cmd_buf[6:8]:
                case '05':
                    ch = 1
                case '06':
                    ch = 2
                case '07':
                    ch = 3
                case '08':
                    ch = 4
            
        if ch == 1:
            header = ['XI_DA','XI_Deri/mV']   
            name = 'XI'
        elif ch == 2:
            header = ['XQ_DA','XQ_Deri/mV']   
            name = 'XQ'
        elif ch ==3:
            header = ['YI_DA','YI_Deri/mV'] 
            name = 'YI'  
        elif ch == 4:
            header = ['YQ_DA','YQ_Deri/mV'] 
            name = 'YQ'  
        elif ch ==5:
            header = ['XP_DA','XP_Deri/mV']  
            name = 'XP' 
        elif ch == 6:
            header = ['YP_DA','YP_Deri/mV']  
            name = 'YP' 

        # csv文件名称
        filename = './log/' + CDM_SN + '/' + CDM_SN +'_'+ str(CDM_T0) +'c_'+ str(CDM_WL0) + '/' + name+ '_LockCalibration'+'_'+ self.Time_text()+'.csv'
        # filename1 = './log/' + CDM_SN + '/' + CDM_SN +'_'+ str(CDM_T0) +'c_'+ str(CDM_WL0) + '/' + name+ '_LockCalibration_plot'+'_'+ self.Time_text()
                
        self.textBroswerPrintRealTime('CSV创建完成, 保存路径:'+'./log/' + CDM_SN + '/' + CDM_SN +'_'+ str(CDM_T0) +'c_'+ str(CDM_WL0) + '/') 
        self.textBroswerPrintRealTime('filename: '+ name+ '_LockCalibration'+'_'+ self.Time_text()+'.csv')
                                    
                                    

        #2*9的二维数组
        array_buf =  [[0] * length for _ in range(2)]#二维矩阵
        array =  [[0] * length for _ in range(2)]#二维矩阵
        
        for i in range(9):
            array_buf[0][i] = self.Rx_Array_buf[i+1]
        for i in range(9):
            array_buf[1][i] = self.Rx_Array_buf[i+9+1]
        
        for i in range(2):
            self.LockCalibrationData_process(array_buf[i], length, array[i], length_flg[i])#一次性读取  WordNum*6个字节的长数据
            self.textBroswerPrintRealTime(str(i)+'.获取记录中...')
        
        for i in range (length):
            array[1][i] = array[1][i]*10                     

                
        #所有数据存进CSV
        data = list(zip(*array))  # 行列转换
        # write in DAdata   
        with open(filename, 'a', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)
            for i in data:#  write in CSV
                writer.writerow(i)
            csvfile.close()    

        self.plot_Line( ch, filename, array, length)
        
    def LockCalibrationData_process(self, RxArray, cycle, array, flag):#处理数据即可  WordNum*6个字节的长数据
        
            if flag == 0:  # 读取DA
                for cycle_buf in range(cycle):
                    array[cycle_buf]= '0x'+RxArray[cycle_buf][-4:]#转化为带0x的4位16进制数
            if flag == 1:#读取Scan null data、Scan null CurveValue
                for cycle_buf in range(cycle):
                    try:
                        if RxArray[cycle_buf][-5:-4]== '0':
                            array[cycle_buf] = int(RxArray[cycle_buf][-4:],16)/10000.0
                        else:
                            array[cycle_buf] = 0-int(RxArray[cycle_buf][-4:],16)/10000.0
                    except:
                        print(RxArray, '4')
                        self.textBroswerPrintRealTime('数据出错')
                        
    def plot_Line(self, ch, filename1, Array_Da, DitherCala_num):
    
        plt.figure()
        name= ''
        #拟合Phase_Err

        if ch == 5:
            name = ' XPhase_offset'
        elif ch == 6:
            name = ' YPhase_offset'
            
        array_num = DitherCala_num
        #X和Y都为2*7的二维数组，record存放顺序 
        array_buf =  [[0] * array_num for _ in range(2)]#二维矩阵

        for i in range(array_num):
            array_buf[0][i] = i
            array_buf[1][i] = Array_Da[1][i]
            
        
        slope,intercept = np.polyfit(array_buf[0],array_buf[1],1)#一阶直线拟合
        # print('一阶线性拟合：',slope,intercept)
        #X和Y都为2*7的二维数组，record存放顺序 
        record =  [[0] * 2 for _ in range(2)]#二维矩阵
        #先画图，再保存 斜率和截距到数组，转存到CSV,科学计数法 "{:.3e}".format(slope)
        record[0][0] = 'slope:'
        record[1][0] = "{:.3e}".format(slope)
        record[0][1] = 'intercept:'
        record[1][1] = "{:.3e}".format(intercept)    
        
        for i in range(array_num):
            array_buf[1][i] = slope*np.float64(array_buf[0][i])+intercept

        plt.plot( array_buf[0], Array_Da[1] , marker = 'o', color = 'b')
        plt.plot( array_buf[0], array_buf[1], marker = 'o', color = 'r')
        plt.xlabel('DA')
        plt.ylabel('offset_value')
        plt.title(name)#MPD_Resp
        

        plt.text(max(array_buf[0])*0.3,min(Array_Da[1])*0.8,'x = '+ str(array_buf[0][int(DitherCala_num/2)])+' , y='+str(slope*np.float64(array_buf[0][int(DitherCala_num/2)])+intercept)[:5] ,fontsize = 10,c = 'b')
        plt.text(max(array_buf[0])*0.3,min(Array_Da[1]),'a*x+β: '+str(record[1][0])+' *x + '+str(record[1][1]) ,fontsize = 10,c = 'b')

        plt.savefig(filename1+ str(name)+".png")            
   
        plt.show()   
        
        #所有数据存进CSV
        data = list(zip(*array_buf))  # 行列转换
        data1 = list(zip(*record))  # 行列转换
        header = {'x','y'}
        # write in DAdata   
        with open(filename1, 'a', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)
            for i in data:#  write in CSV
                writer.writerow(i)
            for i in data1:#  write in CSV
                 writer.writerow(i)    
            csvfile.close()                 


    def Calibrate_OneThreshold_LoopDone(self):

        #最大门限
        Max_DitherAmp = self.setting_CDM.value("setup_Calibrate_Locking/Max_DitherAmp_MaxMaxMax")
        Flag_MZ_Channel = self.setting_CDM.value("setup_Calibrate_Locking/Flag_MZ_Channel")
        
        # data = list(zip(*self.record_Power))  # 行列转换
        # 每次按行写入, 等所有循环结束，再统一处理数据
        try:
            with open(self.FlieName, 'a', encoding='utf-8-sig', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(self.Array_For_Calibrate)
                # for i in data:#  write in CSV
                #     writer.writerow(i)
                csvfile.close()   
        except:
            print('保存数据出错')
        Amp = self.Amp + self.Amp_Step  
        self.setting_CDM.setValue("setup_Calibrate_Locking/Current_DitherAmp", Amp)    
        sleep(0.001)
        # #判断当前次的 Amp值是否到达最大的Max_DitherAmp？
        # #如果未达到则继续调用 锁定函数进行循环
        if Amp <= int(Max_DitherAmp):  
            if Flag_MZ_Channel == 1:
                self.Trigger_Calibrate_X_IQ_Loop.emit()
                #当等于 Max_DitherAmp时，会是最后一次继续调用锁定函数，但是不进行锁定循环，只进行所有数据的统一处理   
                #然后结束 所有循环
            elif Flag_MZ_Channel == 2:
                self.Trigger_Calibrate_Y_IQ_Loop.emit()    
            elif Flag_MZ_Channel == 3:

                self.Trigger_Calibrate_XP_Loop.emit()  
            elif Flag_MZ_Channel == 4:
                self.Trigger_Calibrate_YP_Loop.emit()  
        else:
            self.Stop()
                
    def Stop(self): # 
        self.QTread_Run_flag = False
        
    def Rx_Run_Stop(self): # 
        self.Run_flag = False

    def Rx_Run_start(self): # 
        self.Run_flag = True        
    #子线程在调用start()后，就一直在run()中循环，一旦里面的while结束则子线程也就结束了
    #只有子线程一直存在，才能随时 接收来自主进程的信息 或者 向外发送信息
    #也只有在run()中，进行 信息的等待、接收、处理 或者 给主程序回送消息，GUI才不卡顿    
    def run(self): # Uart_Rx_程序，打印数据
        i = 0
        log = '..'
        self.QTread_Run_flag = True
        self.Run_flag = True
        self.Trigger_Uart_StartFlag.emit(self.Flag_Clear)
        
        sleep(0.001)
        try:
            #进入轮询：1.等待RX回复 指令执行完毕，回复 'AFAF'； 或者 等待RX回复 指令所需回读的数据
            while self.QTread_Run_flag:
                self.Flag_Clear = False
                self.error_flag = 0#用于处理串口回读出错，防止当前次的串口出错进入串口等待的死循环中，导致锁定无法进行
                #发送指令，自动判断 串口是否发送成功、校验RX是否接收到正确的指令
                self.SendHexCmd(self.cmd, self.Action_Text, self.Action_Num, self.show_flag)
                #大多数的函数都是只执行一次就自动关闭循环
                #锁定函数则一直循环，直至循环次数达到设定值  或者 人为中断锁定
                sleep(0.001)
                if self.setting_CDM.value('setup/LockRecord_EnSave') ==  True:
                    self.Trigger_Refresh_HeaterR.emit()#当前次 锁定完成后，STM32更新一次HeaterR电阻   
                sleep(0.001)             
                
                if self.CalibrateLocking_Flag == True:
                    #触发功率计更新当前光功率 
                    buf = self.setting_CDM.value("setup_Calibrate_Locking/Flag_PowerMeter_ShowResult")
                    buf1 = buf.lower() == "true"
                    self.Trigger_Call_PowerMeter.emit(buf1)  
                    self.CalibrateLocking_cycle_buf = i
                sleep(0.001) 
                    
                if self.DoLocking_Flag == False:#区分长耗时指令和锁定 长耗时指令
                    while self.Run_flag == True:#进入小循环 等待Rx回复
                        match self.Action_Num:    
                            case self.Action_Num_FindPoint:#找点
                                self.textBroswerPrintRealTime('waitting...'+str(i)+str(log*(i//5)))
                                sleep(5)  
                                i = i+5
                            case self.Action_Num_PhAgainFindPoint:#Phase Again FindPoint
                                self.textBroswerPrintRealTime('waitting...'+str(i)+str(log*(i//1)))
                                sleep(1)  
                                i = i+1
                            case self.Action_Num_IQAlignment:#IQ Alignment
                                self.textBroswerPrintRealTime('waitting...'+str(i)+str(log*(i//1)))
                                sleep(0.1)  
                                i = i+1
                            case self.Action_Num_IQLock:#IQ锁定
                                self.textBroswerPrintRealTime('waitting...'+str(i)+str(log*(i//1)))
                                sleep(1)  
                                i = i+1
                            case self.Action_Num_FindPointRecrodSave:#FindPoint数据保存
                                self.textBroswerPrintRealTime('waitting...'+str(i)+str(log*(i//1)))
                                sleep(0.2)  
                                i = i+1
                            case self.Action_Num_LockCalibration:#FindPoint数据保存 
                                self.textBroswerPrintRealTime('waitting...'+str(i)+str(log*(i//1)))
                                sleep(1)  
                                i = i+1                                
                            case '':
                                self.textBroswerPrintRealTime('Cmd有误')  
                        pass
                        self.Stop()#子线程自动结束
                else:#self.DoLocking_Flag =True，循环 锁定                   
                    i=i+1
                    self.Trigger_LockCycle_show.emit(i)#在LockeState控件上，更新锁定次数

                    self.LockCycle_Err = i#用来存放当前锁定失败的次数
                    while self.Run_flag == True:#进入小循环等待Rx回复AFAF,则本次锁定完成
                        self.error_flag = self.error_flag +1#串口出错则进行等待次数的统计，防止完成进入死循环导致锁定无法进行
                        sleep(0.002)
                        if self.error_flag > 2000:# 等待时间达到设定值，直接终止本次的等待，开启新一次的锁定
                            self.Trigger_Uart_StoptFlag.emit()
                            sleep(0.002)
                            self.error_flag = 0
                            self.Flag_Clear = True
                            self.textBroswerPrintRealTime('第 '+str(i)+' 次锁定 返回信息失败，直接开启新一次的锁定')
                            print('199')
                            self.Rx_Run_Stop()#一旦当前次的锁定失败，直接开启新一轮的锁定
                            print('199-1')                             
                            break   

                    if i < self.LockCycle_Target:#锁定未达到目标次数
                        self.error_flag = 0
                        print('120')
                        self.Trigger_Uart_StoptFlag.emit()#结束了一次锁定和串口通信
                        sleep(0.002)
                      
                        #串口线程重新启动
                        self.Trigger_Uart_StartFlag.emit(self.Flag_Clear)
                        sleep(0.002)
                        print('120-1')
                        self.Rx_Run_start()#线程中的小循环 重新启动
                        
                    else:#锁定达到目标次数或者人为终止锁定，结束锁定
                        self.COM_Settings.emit(True) 
                        self.Trigger_LockStop.emit(i)#   
                        sleep(0.1)
                        if self.CalibrateLocking_Flag == True:
                            print('33333333333')
                            sleep(0.2)
                            self.Calibrate_OneThreshold_LoopDone()                        
                        self.Stop()#停止锁定，子线程自动结束
                        print('结束')

        except:
            print('(QThread) RunFail')
            self.textBroswerPrintRealTime('(QThread) RunFail')
            self.Trigger_Uart_ClearBuffer.emit()
            
            
            
