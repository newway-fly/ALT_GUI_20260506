# import socket
import re

import pyvisa 

#波长   :FETC'+str(ch)+':CHAN'+str(port)+':POW?

class TCPIP_Socket(object):
    def __init__(self):

        # self为当前文件自定义的类：SerialPortA_Tool本身，必要的触发信号和槽函数 可在这该文件实现
        # parent为传递过来的UI界面的本身，以它为对象进行UI界面操作，且想要对UI界面的操作必须是它为归属 parent.xxx
        self.err = 0

        self.s = ''#Socket对象
        self.HOST = ''
        self.PORT = ''

    def setup_newSocket(self,your_host, your_port='' ):
        #创建一个Socket对象并指定主机名（或者IP地址）和端口号。然后调用connect()函数与光功率计建立连接。
        self.HOST = your_host # 设置主机名或IP地址
        self.PORT = your_port # 设置端口号

        rm = pyvisa.ResourceManager() # 打开visa的资源管理器实例化
        try:
            # self.instrument = rm.open_resource('TCPIP::192.168.0.112::INSTR')
            self.instrument = rm.open_resource( 'TCPIP::'+your_host +'::INSTR' )
     
            Dvive_Info = self.instrument.query('*IDN?')
            return Dvive_Info
        except:
            return False
    
    
    def SendCmd(self,cmd):
        try:
            self.instrument.write(cmd)#设置要发送的命令
            # print(cmd,'指令下发成功')
            return  True
        except:
            return  False
        
    def SendCmd_GetData(self,cmd):
        try:
            info = self.instrument.query(cmd)#设置要发送的命令
            # print(cmd,'指令下发成功')  
            return re.sub(r"\s+", "", info)
        except:
            return  False
        
    def Socket_Close(self):
        try:
            self.instrument.close()
            # print('断开连接')
            return  True
        except:
            return  False