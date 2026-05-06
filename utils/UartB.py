from PyQt5 import QtWidgets,QtCore
from PyQt5.QtCore import QThread,pyqtSignal
import serial
from time import sleep

'''
编写与单片机 通信的底层函数
'''
class Uart_Tool(QThread):
    
    Tx_HexSignal = pyqtSignal(str, int, list)#自定义信号：串口需启动发送的signal，用于接收来自主函数的Tx指令 
    Tx_CharSignal = pyqtSignal(str, bool, bool)#自定义信号：串口需启动发送的signal，用于接收来自主函数的Tx指令 
    Rx_data_WordNum_array= pyqtSignal(list)
    
    def __init__(self, Uart_TxFinish_Flag, Uart_RebackSignal_Flag, RxCheck_TxSignal_flag, Uart_Reback_QThreadFinish_Signal_flag, Uart_Rx_Array):
        super().__init__()#调用 父类中的__init__()方法



        # 设置串口配置文件的路径 加载内容
        self.setting = QtCore.QSettings("./data/config_Board.ini", QtCore.QSettings.IniFormat)
        self.setting.setIniCodec("UTF-8")#设置格式
        # 设置CDM配置文件的路径 加载内容
        self.setting_CDM = QtCore.QSettings("./data/config_CDM.ini", QtCore.QSettings.IniFormat)
        self.setting_CDM .setIniCodec("UTF-8")#设置格式
        
        # self为Uart_Tool自定义的内容，必要的触发信号，可在后续需要的地方进行调用
        self.TxFinish = Uart_TxFinish_Flag
        self.RebackSignal = Uart_RebackSignal_Flag
        self.RxReceiveTx_Check = RxCheck_TxSignal_flag
        self.Reback_QThreadFinish_Signal = Uart_Reback_QThreadFinish_Signal_flag

        self.num_break = 0
        self.Rx_Array = Uart_Rx_Array
        self.Rx_Array_ID = 0   #  便于Rx_Array计数
        self.DataShow_flag = ['']*3
        
        self.QThread_Run_Flag = False     #串口子线程的使能标志位
 
        self.Rx_data = 'None'               #接收原始数据
        self.Rx_data_buf = 'None'           #原始数据进行解码
        self.Rxdata_Num = 0
        
        
        self.TxCmd = ''
        self.Action_Num = 0
        self.Rx_data_WordNumSel = True
        self.Rx_data_WordNum = 6
        
        self.Rx_data_WordNum_Array = ''
      
        #自定义信号绑定槽函数
        self.Tx_HexSignal.connect(self.Uart_Tx)
        self.Tx_CharSignal.connect(self.Uart_Tx_Char)
        self.Rx_data_WordNum_array.connect(self.array_copy)


        
    def array_copy(self, array):
        self.Rx_data_WordNum_Array = array

    def Clear_DataBuffer(self):
        # self.Rx_data = self.custom_serial.readline()#串口出错后  用来清空
        self.Rx_data = self.custom_serial.readall()#串口出错后  用来清空
        # self.QThread_Run_Flag = False
        print('121')
        

    #关闭串口
    def SerialPort_Close(self):
        try:
            self.custom_serial.close()
            return True
        except:
            return False
    #打开串口
    def SerialPort_Open(self, SerialPort_COM, SerialPort_Baud):
        try:
            self.custom_serial = serial.Serial(SerialPort_COM, int(SerialPort_Baud), timeout=0.01, writeTimeout=0.01)
            if self.custom_serial.isOpen():
                return True
        except:
            return False

    #发送指令,Tx_HexSignal
    def Uart_Tx(self, Tx_Signal, ActionNum, show_flag):
        #Tx_HexSignal要发送之前,触发接收线程启动,然后发送指令
        self.Rx_Array_ID = 0
        self.QThread_Run_Flag = True

        self.Action_Num = ActionNum
        self.Rxdata_Num = show_flag[0]
        
        self.DataShow_flag[0] = show_flag[0]
        self.DataShow_flag[1] = show_flag[1]
        self.DataShow_flag[2] = show_flag[2]
  
        self.TxCmd = Tx_Signal#转存
        
        try:
            # encode()函数是编码，把字符串数据转换成bytes数据流
            # 16进制字符串,Hex转换成bytes数据流,Hex之间必须有空格隔开，如FF 07 00 01 FF FF
            # ASCII字符串, 直接encode()转换即可
            data = bytes.fromhex(Tx_Signal)
            self.custom_serial.write(data)            

            #必须有返回值，发送函数需判断发送是否成功 return True

            self.TxFinish.emit(Tx_Signal, True, show_flag) #Rx信息不打印，Tx成功发送的标志位也不打印
            
        except:
            # return False
            self.TxFinish.emit(Tx_Signal, False,  show_flag)
    #发送指令,Tx_HexSignal
    def Uart_Tx_Char(self, Tx_CharSignal, Action, ActionNum, show_flag):
        #Tx_HexSignal要发送之前,触发接收线程启动,然后发送指令
        self.Rx_Array_ID = 0

        self.Action_Num = ActionNum
        self.Rxdata_Num = show_flag[0]
        self.DataShow_flag[0] = show_flag[0]
        self.DataShow_flag[1] = show_flag[1]
        self.DataShow_flag[2] = show_flag[2]
  
        
        self.TxCmd = Tx_CharSignal#转存
        
        try:
            # encode()函数是编码，把字符串数据转换成bytes数据流
            # 16进制字符串,Hex转换成bytes数据流,Hex之间必须有空格隔开，如FF 07 00 01 FF FF
            # ASCII字符串, 直接encode()转换即可
            self.custom_serial.write(Tx_CharSignal.encode())         

            #必须有返回值，发送函数需判断发送是否成功 return True

            self.TxFinish.emit(Tx_CharSignal, Action, True, show_flag)#Rx信息不打印，Tx成功发送的标志位也不打印
            
        except:
            # return False
            self.TxFinish.emit(Tx_CharSignal, Action, False,  show_flag)

    def Stop(self): # 
        self.QThread_Run_Flag = False
        self.setting.setValue("setup_SerialPortB/Flag_Stop", False)
        sleep(0.001)
        
    #子线程在start()后就一直在run()中，一旦run()中的while结束，则子线程也就结束了
    #只有子线程一直存在，才能随时接受来自主进程的信息
    #也只有在run()中，进行 信息的等待、接收、给主程序回送消息，主线程UI才不卡顿
    def run(self): # Rx子线程，子线程发送自定义信号只能加载到UI主线程的事件队列里，延后执行
        self.Rx_Array_ID = 0
        self.QThread_Run_Flag = True
        self.setting.setValue("setup_SerialPortB/Flag_Stop", True)
        sleep(0.001)
        i = 0
        while self.QThread_Run_Flag:#串口一旦启动,Rx子线程的使能标志位为True
            # print('轮询...')
            try:
                if self.Rx_data_WordNumSel == False:
                    self.Rx_data = self.custom_serial.read(int(self.Rx_data_WordNum_Array[self.Rx_Array_ID]))
                elif self.Rx_data_WordNumSel == True:
                    self.Rx_data = self.custom_serial.read(6)#12
                self.Rx_Array[self.Rx_Array_ID] = self.Rx_data.hex().upper()  # 接收数据里面赋值给变量，方便传递
                self.Rx_Array_ID = self.Rx_Array_ID + 1 

                # print(self.Rx_Array)
                # print(self.Rx_Array_ID)  
                    
                if self.Rx_Array_ID == 1 and self.Rx_Array[self.Rx_Array_ID-1] != '':
                    self.RxReceiveTx_Check.emit(self.TxCmd, self.Rx_Array[0], self.DataShow_flag)#回复TxCmd和原指令 进行校验
                else:
                    #长耗时--指令,可能执行操作，也可能返回长数据
                    if self.Action_Num >= 1000:
                        #执行操作过程，伴随返回数据
                        if  self.Rx_Array[self.Rx_Array_ID-1] == '':
                            self.Rx_Array_ID = self.Rx_Array_ID - 1    #控制数组的下标，等待真正的数据

                        elif self.Rx_Array[self.Rx_Array_ID-1][-4:] == 'AFAF':    #等于'AFAF'时，执行完毕
                                self.Reback_QThreadFinish_Signal.emit(self.Action_Num, self.DataShow_flag)
                                self.Stop()
                                # break
                        elif int(len(self.Rx_Array[self.Rx_Array_ID-1])) != int(self.Rx_data_WordNum_Array[self.Rx_Array_ID - 1])*2:#串口回读出错，拼接数据
                            
                            # buff = self.custom_serial.read( int(self.Rx_data_WordNum_Array[self.Rx_Array_ID - 1])*2 - int(len(self.Rx_Array[self.Rx_Array_ID-1])) )
                            # self.Rx_Array[self.Rx_Array_ID-1] = self.Rx_Array[self.Rx_Array_ID-1] +  buff.hex().upper()
                            t = 0
                            while(1):
                                buff = self.custom_serial.readline()
                                self.Rx_Array[self.Rx_Array_ID-1] = self.Rx_Array[self.Rx_Array_ID-1] +  buff.hex().upper()
                                t = t+1
                                sleep(0.001)
                                if t > 20:
                                    break
                                # print(buff.hex().upper(),'******')
                                if int(len(self.Rx_Array[self.Rx_Array_ID-1])) == int(self.Rx_data_WordNum_Array[self.Rx_Array_ID - 1])*2:
                                    break
                    else:#短耗时--指令,可能执行操作，也可能返回长数据
                        i = i+1
                        if i >1000:
                            self.Stop()
                        if self.Rx_Array_ID == self.Rxdata_Num and self.Rx_Array[self.Rx_Array_ID-1] != '':
                            #短耗时--指令 无需回传，主程序直接等待
                            self.Stop()
                        else:
                            self.Rx_Array_ID = self.Rx_Array_ID - 1    #控制数组的下标，等待真正的数据的回传

            except:
                print('接收失败')
                self.Stop()#接收失败也直接结束本次循环