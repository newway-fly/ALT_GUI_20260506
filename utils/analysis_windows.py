# utils/analysis_windows.py
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextBrowser
import PyQt5.QtCore
import numpy as np
from scipy.fft import fft, fftfreq

class AnalysisWindow(QWidget):
    """独立的绘图子窗口基类"""
    def __init__(self, title="Analysis Window", width=1000, height=800):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(width, height)
        self.layout = QVBoxLayout(self)
        
        # 顶部的文本诊断报告框
        self.text_browser = QTextBrowser()
        self.text_browser.setMaximumHeight(100)
        self.text_browser.setStyleSheet("font-weight: bold; color: blue; background-color: #F0F0F0;")
        self.layout.addWidget(self.text_browser)
        
        # 底部的 PyQtGraph 极速绘图面板
        self.graph_layout = pg.GraphicsLayoutWidget()
        self.graph_layout.setBackground('w') # 白底
        self.layout.addWidget(self.graph_layout)

class FFTPlotWindow(AnalysisWindow):
    def __init__(self, data_list, fs=19200.0, is_noise=False):
        title = "Noise Diagnostic (纯直流底噪分析)" if is_noise else "P22 FFT Analysis (相干信号分析)"
        super().__init__(title)
        
        data = np.array(data_list)
        N = len(data)
        if N < 10: return
        
        # 1. 核心算法：去 DC
        dc_val = np.mean(data)
        ac_data = data - dc_val
        
        ac_data[0] = 0
        ac_data[1] = 0
        ac_data[2] = 0


        # 2. 时域绘图
        t = np.arange(N) / fs * 1000  # ms
        p1 = self.graph_layout.addPlot(title=f"时域波形 (DC={dc_val:.3f}V, N={N})")
        p1.plot(t, ac_data * 1000, pen=pg.mkPen('b', width=1.5))
        p1.setLabel('left', "Voltage (mV)")
        p1.setLabel('bottom', "Time (ms)")
        p1.showGrid(x=True, y=True)
        
        self.graph_layout.nextRow()
        
        # 3. FFT 算法
        yf = fft(ac_data)
        xf = fftfreq(N, 1/fs)
        
        # 取正半轴
        idx_pos = np.where((xf >= 0) & (xf <= 2000)) # 限制看 2kHz 以内
        freqs = xf[idx_pos]
        mags = 2.0 / N * np.abs(yf[idx_pos])
        mags_db = 20 * np.log10(mags + 1e-12)
        
        # 4. 频域绘图
        p2 = self.graph_layout.addPlot(title="频域幅值谱 (dB)")
        p2.plot(freqs, mags_db, pen=pg.mkPen('r', width=1.5))
        p2.setLabel('left', "Magnitude (dB)")
        p2.setLabel('bottom', "Frequency (Hz)")
        p2.showGrid(x=True, y=True)
        
        # 5. 诊断文本输出
        if is_noise:
            median_noise = np.median(mags_db)
            p2.addLine(y=median_noise, pen=pg.mkPen('g', style=pg.QtCore.Qt.DashLine))
            report = f"【环境噪声报告】\n平均直流: {dc_val:.4f} V\n底噪中值: {median_noise:.2f} dB"
        else:
            report = f"【特征频点提取报告】 (DC: {dc_val:.4f}V)\n"
            target_freqs = [400, 800, 1200, 1600]
            colors = ['g', 'm', 'c', 'k']
            for i, target_f in enumerate(target_freqs):
                # 寻找最接近的频点
                idx = np.argmin(np.abs(freqs - target_f))
                mag_mv = mags[idx] * 1000
                report += f">>> {target_f:4d} Hz: 幅度 = {mag_mv:.4f} mV\n"
                
                # 在图上画垂直虚线标出特征频率
                p2.addLine(x=target_f, pen=pg.mkPen(colors[i], style=pg.QtCore.Qt.DashLine))
                
        self.text_browser.setText(report)

class GridPlotWindow(AnalysisWindow):
    def __init__(self, data_dict, title_prefix="Scan Result"):
        super().__init__(f"{title_prefix} - 6 Channels", width=1200, height=800)
        self.text_browser.setText(f"【{title_prefix} 极值与摆幅诊断报告】\n")
        
        # 标准通道顺序 (2行3列)
        order = ['XQ', 'XI', 'XP', 'YQ', 'YI', 'YP']
        
        report = ""
        for i, ch in enumerate(order):
            if ch not in data_dict: continue
            
            raw_data = data_dict[ch]
            if len(raw_data) == 0: continue
            
            # --- 核心诊断：区分 1D 还是 2D ---
            # 如果列表里的元素是一个元组/列表 (代表 DA, PD)，则是 2D 数据
            if isinstance(raw_data[0], (list, tuple)) and len(raw_data[0]) >= 2:
                np_data = np.array(raw_data)
                x_data = np_data[:, 0]  # 第一列是 DA 值
                y_data = np_data[:, 1]  # 第二列是 光电流
            else:
                y_data = np.array(raw_data)
                x_data = np.arange(len(y_data))  # 自动生成 X 轴索引
                
            # 画图
            p = self.graph_layout.addPlot(title=f"Channel: {ch} (Points: {len(y_data)})")
            p.plot(x_data, y_data, pen=pg.mkPen('b', width=1.5), symbol='o', symbolSize=4, symbolBrush='b')
            p.setLabel('bottom', 'DA Value' if isinstance(raw_data[0], (list, tuple)) else 'Index')
            p.setLabel('left', 'Photocurrent')
            p.showGrid(x=True, y=True)
            
            if (i + 1) % 3 == 0:
                self.graph_layout.nextRow()
                
            # 计算数据特征
            d_max, d_min = np.max(y_data), np.min(y_data)
            
            # 找到极值对应的 DA 点 (仅在 2D 模式下有意义)
            if isinstance(raw_data[0], (list, tuple)):
                max_da = x_data[np.argmax(y_data)]
                min_da = x_data[np.argmin(y_data)]
                report += f"[{ch}] Max={d_max:.5f}(@DA:{int(max_da)}), Min={d_min:.5f}(@DA:{int(min_da)})\n"
            else:
                report += f"[{ch}] Max: {d_max:.5f}, Min: {d_min:.5f}, Vpp: {d_max-d_min:.5f}  |  "
                if (i + 1) % 3 == 0: report += "\n"
            
        self.text_browser.append(report)