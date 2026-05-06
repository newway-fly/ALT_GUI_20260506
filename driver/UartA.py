# -*- coding: utf-8 -*-
# 导入包和模块
# from PyQt5.Qt import *

from PyQt5.QtCore import QObject,pyqtSignal
import serial,threading
import serial.tools.list_ports
from time import sleep

'''
编写与单片机 通信的底层函数
'''
class Uart_Tool(QObject):
    
    Tx_Signal = pyqtSignal(str, list, str, int)#自定义信号：串口需启动发送的signal，用于接收来自主函数的Tx指令 
    Tx_DRV_Signal = pyqtSignal(str, list, str, int)#自定义信号：串口需启动发送的signal，用于接收来自主函数的Tx指令 

    def __init__(self, Uart_TxFinish_Flag, Uart_RebackSignal_Flag, Uart_Rx_Array):
        super().__init__()#调用 父类中的__init__()方法
        
        # self为Uart_Tool自定义的内容，必要的触发信号，可在后续需要的地方进行调用
        self.TxFinish_Flag = Uart_TxFinish_Flag
        self.Rebackdata = Uart_RebackSignal_Flag

        self.Rx_Array = Uart_Rx_Array
        self.Rx_Array_ID = 0   #  便于Rx_Array计数
        self.ID_buf = 0   #  防止FW板子没上电，无回应，Uart进入等待的死循环
        
        self.Rx_thread_Flag = False     #串口子线程的使能标志位
        self.Rx_data_Flag = False       #根据Tx发送触发Rx接收的标志位
        
        self.Rx_data = 'None'           #接收原始数据
        self.Rx_data_buf = 'None'       #原始数据进行解码
        self.CmdType_flag = 'None'
        self.DoneNum_ID = 0
        
        self.print_info = ['']*3        #返回信息的标志位 数组
        self.str_buf = ''               #返回 指令缓存区，便于提取有用信息
        
        #自定义信号绑定槽函数
        self.Tx_Signal.connect(self.Uart_Tx)
        self.Tx_DRV_Signal.connect(self.Uart_TxDRV)


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
            self.custom_serial = serial.Serial(SerialPort_COM, int(SerialPort_Baud), timeout=0.008, writeTimeout=0.008)
            if self.custom_serial.isOpen():
                return True
        except:
            return False

    #发送指令,Tx_Signal
    def Uart_Tx(self, Tx_Signal='', show_flag=[1,True,True], DRV_Cmd_flag='', DoneNum=0):
        #Tx_Signal要发送之前,触发接收线程启动,然后发送指令
        self.Rx_data_Flag = True
        self.Rx_Array_ID = 0
        self.ID_buf = 0
        self.print_info[0] = 1
        self.print_info[1] = show_flag[1]
        self.print_info[2] = show_flag[2]
        self.CmdType_flag = DRV_Cmd_flag
        self.DoneNum_ID = DoneNum
        
        self.str_buf = Tx_Signal
        try:
            # encode()函数是编码，把字符串数据转换成bytes数据流
            # 16进制字符串,Hex转换成bytes数据流,Hex之间必须有空格隔开，如FF 07 00 01 FF FF
            # ASCII字符串, 直接encode()转换即可
            self.custom_serial.write((Tx_Signal+'\r\n').encode())

            #必须有返回值，发送函数需判断发送是否成功
            # return True

            self.TxFinish_Flag.emit( True, show_flag, self.CmdType_flag, Tx_Signal) #Rx信息不打印，Tx成功发送的标志位也不打印
            
        except:
            # return False
            self.TxFinish_Flag.emit( False, show_flag, self.CmdType_flag, Tx_Signal)

    #发送指令,Tx_Signal
    def Uart_TxDRV(self, Tx_Signal='', show_flag=[1,True,True], DRV_Cmd_flag='', DoneNum=0):
        #Tx_Signal要发送之前,触发接收线程启动,然后发送指令
        self.Rx_data_Flag = True
        self.Rx_Array_ID = 0
        self.ID_buf = 0
        self.print_info[0] = 1
        self.print_info[1] = show_flag[1]
        self.print_info[2] = show_flag[2]
        self.CmdType_flag = DRV_Cmd_flag
        self.DoneNum_ID = DoneNum
        
        self.str_buf = Tx_Signal
        
        try:
            # encode()函数是编码，把字符串数据转换成bytes数据流
            # 16进制字符串,Hex转换成bytes数据流,Hex之间必须有空格隔开，如FF 07 00 01 FF FF
            # ASCII字符串, 直接encode()转换即可
            self.custom_serial.write((Tx_Signal+'\r\n').encode())
            #必须有返回值，发送函数需判断发送是否成功
            # return True
            self.TxFinish_Flag.emit( True, show_flag, self.CmdType_flag, Tx_Signal) #Rx信息不打印，Tx成功发送的标志位也不打印
            
        except:
            # return False
            self.TxFinish_Flag.emit( False, show_flag, self.CmdType_flag, Tx_Signal)
        
    #子线程在start()后就一直在run()中，一旦run()中的while结束，则子线程也就结束了
    #只有子线程一直存在，才能随时接受来自主进程的信息
    #也只有在run()中，进行 信息的等待、接收、给主程序回送消息，主线程UI才不卡顿
    
    def Uart_Rx(self): # Rx子线程，子线程发送自定义信号只能加载到UI主线程的事件队列里，延后执行
        
        while self.Rx_thread_Flag:#串口一旦启动,Rx子线程的使能标志位为True
            if self.Rx_data_Flag == True:#根据Tx按需触发Rx接收
                # print('轮询...')
                try:
                    self.Rx_data = self.custom_serial.readline()
                    self.Rx_data_buf = bytes.decode(self.Rx_data).strip().strip()#去掉\r\n
                    sleep(0.002)
                    if self.Rx_data_buf != '>':     
                        if self.Rx_data_buf != '':# ''为STM32前面回复的字符，不保存
                            self.Rx_Array[self.Rx_Array_ID] = self.Rx_data_buf
                            self.Rx_Array_ID = self.Rx_Array_ID + 1
                            
                        else:
                            self.ID_buf = self.ID_buf+ 1
                        if  self.ID_buf > 200:#防止进入死循环
                            
                                self.Rx_Array[0] = '接收失败'
                                self.Rebackdata.emit( self.print_info, self.CmdType_flag, self.DoneNum_ID, self.str_buf)#数据接收完成,进行回传
                                self.Rx_data_Flag = False
                                
                    # '>'为STM32最后1次回复的终止字符，不保存
                    else: #self.Rx_data_buf =='>':   
                        # print(self.Rx_Array)
                        # print(self.Rx_Array_ID)
                        
                        self.print_info[0] = self.Rx_Array_ID

                        self.Rebackdata.emit( self.print_info, self.CmdType_flag, self.DoneNum_ID, self.str_buf)#数据接收完成,进行回传
                        #本次接收完成
                        self.Rx_data_Flag = False
                except:
                    # print('接收失败')
                    self.Rx_Array[0] = '接收失败'
                    self.Rebackdata.emit( self.print_info, self.CmdType_flag, self.DoneNum_ID, self.str_buf)#数据接收完成,进行回传
                    self.Rx_data_Flag = False

    def Uart_Rx_ThreadStart(self):
        
        self.Rx_data_Flag = False
        # 建立子线程, 调用Rx程序
        self.Rx_thread_Flag = True#触发轮询启动
        self.Rx_thread = threading.Thread(target=self.Uart_Rx, daemon=True)
        self.Rx_thread.start()

    def Uart_Rx_ThreadOver(self):
        # Rx接收结束线程, 结束Rx程序
        self.Rx_thread_Flag = False




