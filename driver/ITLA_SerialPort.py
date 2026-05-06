from PyQt5.QtCore import QObject,pyqtSignal
import serial,threading
import serial.tools.list_ports
from time import sleep

'''
编写与单片机 通信的底层函数
'''
class Uart_ITLA(QObject):
    

    Tx_HexSignal = pyqtSignal(str, list)#自定义信号：串口需启动发送的signal，用于接收来自主函数的Tx指令 

    
    def __init__(self, Uart_TxFinish_Flag, Uart_RebackSignal_Flag, Uart_Rx_Array):
        super().__init__()#调用 父类中的__init__()方法
        
        # self为Uart_Tool自定义的内容，必要的触发信号，可在后续需要的地方进行调用
        self.TxFinish_Flag = Uart_TxFinish_Flag
        self.RebackSignal = Uart_RebackSignal_Flag
        # self.RxReceiveTx_Check = RxReceiveTx_Signal
    
        self.Rx_Array = Uart_Rx_Array
        self.Rx_Array_ID = 0   #  便于Rx_Array计数
        self.Print_flag = [1,True,True]
        
        self.Rx_thread_Flag = False     #串口子线程的使能标志位
        self.Rx_data_Flag = False       #根据Tx发送触发Rx接收的标志位
        self.Rx_data = 'None'           #接收原始数据
        self.Rx_data_buf = 'None'       #原始数据进行解码

    
        self.Tx_HexSignal.connect(self.Uart_Tx_Char)
        

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
            self.custom_serial = serial.Serial(SerialPort_COM, int(SerialPort_Baud), timeout=0.05, writeTimeout=0.05)
            if self.custom_serial.isOpen():
                return True
        except:
            return False


    #发送指令,Tx_HexSignal
    def Uart_Tx_Char(self, Tx_Signal, show_flag):
        #Tx_HexSignal要发送之前,触发接收线程启动,然后发送指令
        self.Rx_data_Flag = True
        self.Print_flag[0] = show_flag[0]
        self.Print_flag[1] = show_flag[1]
        self.Print_flag[2] = show_flag[2]
        
        self.Rx_Array_ID = 0

        try:
            # encode()函数是编码，把字符串数据转换成bytes数据流
            # 16进制字符串,Hex转换成bytes数据流,Hex之间必须有空格隔开，如FF 07 00 01 FF FF
            # ASCII字符串, 直接encode()转换即可
            data = bytes.fromhex(Tx_Signal)
            self.custom_serial.write(data)            

            #必须有返回值，发送函数需判断发送是否成功 return True

            self.TxFinish_Flag.emit(Tx_Signal, True,  show_flag) #Rx信息不打印，Tx成功发送的标志位也不打印
            
        except:
            # return False
            self.TxFinish_Flag.emit(Tx_Signal, False, show_flag)
                 
    #子线程在start()后就一直在run()中，一旦run()中的while结束，则子线程也就结束了
    #只有子线程一直存在，才能随时接受来自主进程的信息
    #也只有在run()中，进行 信息的等待、接收、给主程序回送消息，主线程UI才不卡顿
    
    def Uart_Rx(self): # Rx子线程，子线程发送自定义信号只能加载到UI主线程的事件队列里，延后执行
        # self.Rx_Array_ID = 0
        while self.Rx_thread_Flag:#串口一旦启动,Rx子线程的使能标志位为True
            # print('轮询...')
            if self.Rx_data_Flag == True:#根据Tx按需触发Rx接收
                # print('轮询...')
                try:
                    self.Rx_data = self.custom_serial.readline()
                    self.Rx_Array[self.Rx_Array_ID] = self.Rx_data.hex().upper()
                    self.Rx_Array_ID = self.Rx_Array_ID + 1 
                    # print(self.Rx_Array_ID)
                    # print(self.Rx_Array)
                    
                    if self.Rx_Array_ID >= 1:
                        
                        self.Print_flag[0] = self.Rx_Array_ID
                        self.RebackSignal.emit(self.Print_flag, self.Rx_Array)
                        
                        self.Rx_data_Flag = False
                        

                except:
                    print('接收失败')


    def Uart_Rx_ThreadStart(self):
        # 建立子线程, 调用Rx程序
        self.Rx_thread_Flag = True#触发轮询启动
        self.Rx_thread = threading.Thread(target=self.Uart_Rx, daemon=True)
        self.Rx_thread.start()

    def Uart_Rx_ThreadOver(self):
        # Rx接收结束线程, 结束Rx程序
        self.Rx_thread_Flag = False

