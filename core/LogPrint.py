
from PyQt5 import QtWidgets
import sys,os,datetime
sys.path.append(os.getcwd())

from utils.Ui_QTextBrowser_Print import Ui_Form



class LogPrint(QtWidgets.QWidget,Ui_Form):

    def __init__(self,parent=None,*args,**kwargs):#该类一旦实例化，第一时间执行的内容
        super().__init__(parent,*args,**kwargs)#
        #上面直接继承父类QtWidgets.QWidget，会覆盖_rc的背景图，增加这句命令即可
        # self.setAttribute(Qt.WA_StyledBackground, True)
        self.setupUi(self)
        
        
        self.text = ['']*50
        self.text_ID = 0
        self.Print_flag1 = False
        self.Print_flag2 = False
        
        self.Print_thread_Flag = False     #子线程的使能标志位
        self.Print_CDM_GUI = False            #根据Tx发送触发Rx接收的标志位
        self.Print_DRV = False            #根据Tx发送触发Rx接收的标志位
        self.Print_LockPoint = False            #根据Tx发送触发Rx接收的标志位
        self.Print_ITLA = False            #根据Tx发送触发Rx接收的标志位

    def Time_text(self):
        return datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    
    def Print(self, text, list):   
        if list[1] == True:     
            self.textBroswerPrintRealTime(text) 
   
    def textBroswerPrintRealTime(self, text):  
        self.QTextBrowser_Print.append(text)
        self.cursor = self.QTextBrowser_Print.textCursor()
        self.QTextBrowser_Print.moveCursor(self.cursor.End)  # 光标移动到最后，实时信息就可以显示出来
        QtWidgets.QApplication.processEvents()  # 加上此命令，打印过程 GUI不卡顿       
        
        
         
   
