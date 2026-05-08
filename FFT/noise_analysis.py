import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks
import os

# ============================================================
# [铁律] PyQt5 上位机配套专家脚本：高分辨率纯底噪诊断工具
# 功能：自动寻峰、真实环境寄生噪声识别、自适应 Y 轴缩放
# 适用：5760点纯直流模式 (GET_PD_ADC_DATA) 提取的数据
# ============================================================

def noise_analysis(filename='p22.txt', fs=19200.0):
    """
    全自动环境噪声与底噪分析仪
    """
    # ================= 1. 鲁棒性数据加载 =================
    if not os.path.exists(filename):
        print(f"❌ 错误: 找不到文件 {filename}")
        return

    try:
        with open(filename, 'r') as f:
            raw_content = f.read().replace('----BEGIN_DATA----', '').replace('----END_DATA----', '')
            raw_content1 = raw_content.replace('S2', '')
            clean_data = raw_content1.replace(',', ' ').split()
            data = np.array([float(x) for x in clean_data])
    except Exception as e:
        print(f"❌ 数据解析异常: {e}")
        return

    N = len(data)
    if N == 0: return
    
    # ================= 2. 时域基本统计 =================
    t = np.arange(N) / fs
    dc_val = np.mean(data)
    ac_data = data - dc_val  # 强制去直流，提纯交流噪声
    rms_val = np.sqrt(np.mean(ac_data**2))
    v_pp = np.ptp(ac_data)

    # ================= 3. 高分辨率 FFT 计算 =================
    win = np.hanning(N)  # 汉宁窗
    yf = fft(ac_data * win)
    xf = fftfreq(N, 1/fs)
    
    # 取正半轴
    pos_mask = xf >= 0
    freqs = xf[pos_mask]
    # 补偿汉宁窗带来的幅值衰减，并转换为 Vpk
    mags = np.abs(yf[pos_mask]) * 2.0 / np.sum(win)
    # 转换为 dBV 格式，加入 1e-12 防止 log(0) 报错
    mags_db = 20 * np.log10(mags + 1e-12)

    # ================= 4. 智能环境噪声寻峰 (核心更新) =================
    # 动态评估底噪中值
    median_db = np.median(mags_db)
    
    # 使用 find_peaks 盲扫
    # prominence=10 表示峰值必须比周围的谷底高出至少 10dB 才算作独立噪声源
    # distance=int(15) 确保靠得很近的同一个山包只被标记一次 (约 50Hz 间隔)
    peaks_idx, properties = find_peaks(mags_db, prominence=10.0, distance=15)
    
    # 获取所有的峰值频率和幅度
    peak_freqs = freqs[peaks_idx]
    peak_mags_db = mags_db[peaks_idx]
    
    # 按能量大小从高到低排序，找出 Top N 的杀手级噪声
    sort_order = np.argsort(peak_mags_db)[::-1]
    sorted_peak_idx = peaks_idx[sort_order]
    
    # 为了图表美观，图上最多只标记前 10 个最大的刺客噪声
    top_n = min(10, len(sorted_peak_idx))
    display_peaks_idx = sorted_peak_idx[:top_n]

    # ================= 5. 打印终端分析报告 =================
    print("\n" + "="*50)
    print("        96G CDM 硬件环境寄生噪声分析报告")
    print("="*50)
    print(f"【时域统计】")
    print(f"数据深度: {N} 点 | 采样率: {fs/1000:.2f} kHz | 频率分辨率: {fs/N:.3f} Hz")
    print(f"DC 绝对偏置: {dc_val:.4f} V")
    print(f"交流噪声 Vpp: {v_pp*1000:.2f} mV | 噪声 RMS: {rms_val*1000:.3f} mV")
    
    print(f"\n【频域特征 - 自动捕获前 {len(sorted_peak_idx)} 个主要噪声源】")
    print(f"基准底噪中值 (Median Floor): {median_db:.2f} dBV")
    
    if len(sorted_peak_idx) == 0:
        print("✅ 完美！系统非常纯净，未发现突出的周期性噪声刺客。")
    else:
        print("发现以下显著频点 (可能为电源纹波、市电串扰或内部数字时钟耦合):")
        for i, idx in enumerate(sorted_peak_idx):
            f_val = freqs[idx]
            m_val = mags_db[idx]
            v_val = mags[idx] * 1000  # 换算成 mV
            print(f"  [{i+1}] 频率: {f_val:7.2f} Hz | 幅值: {m_val:6.2f} dBV ({v_val:6.3f} mV)")
    print("="*50 + "\n")

    # ================= 6. 自动美化可视化绘图 =================
    plt.figure(figsize=(14, 9))
    plt.rcParams['font.sans-serif'] = ['SimHei'] # 支持中文
    plt.rcParams['axes.unicode_minus'] = False 

    # 子图1: 时域纯噪声波形
    plt.subplot(2, 1, 1)
    plt.plot(t*1000, ac_data * 1000, color='#1f77b4', linewidth=0.8, alpha=0.8)
    plt.title(f'时域交流噪声波形 (去 DC, 共 {N} 点)', fontsize=12)
    plt.xlabel('时间 (ms)')
    plt.ylabel('噪声电压 (mV)')
    plt.grid(True, alpha=0.3)

    # 子图2: 智能寻峰频谱图
    plt.subplot(2, 1, 2)
    plt.plot(freqs, mags_db, color='#2ca02c', linewidth=1.0, label='噪声幅值谱')
    
    # 绘制自动标定的基准底噪线
    plt.axhline(median_db, color='gray', linestyle='--', alpha=0.6, label='底噪中值')
    
    # 在图上用红色 'x' 标记 Top N 的尖峰，并悬浮文字
    for idx in display_peaks_idx:
        fx = freqs[idx]
        fy = mags_db[idx]
        plt.plot(fx, fy, "rx", markersize=6)
        plt.text(fx, fy + 2, f"{fx:.1f}Hz\n{fy:.1f}dB", 
                 ha='center', va='bottom', fontsize=9, color='red', 
                 bbox=dict(facecolor='white', alpha=0.5, edgecolor='none', pad=1))

    plt.title('全频段寄生噪声侦测谱 (dB 坐标系)', fontsize=12)
    plt.xlabel('频率 (Hz)')
    plt.ylabel('幅值 (dBV)')
    plt.xlim(0, max(4000, np.max(freqs[display_peaks_idx]) + 500) if len(display_peaks_idx) > 0 else 4000)
    
    # 【关键更新】: 纵轴动态自适应逻辑
    # 下限：底噪中值往下 15dB；上限：最大尖峰往上 15dB
    y_max = np.max(mags_db) if len(mags_db) > 0 else 0
    y_min = median_db - 15
    plt.ylim(y_min, y_max + 15)
    
    plt.grid(True, which='both', alpha=0.3)
    plt.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig('./FFT/Noise_Diagnostic_Report.png', dpi=300)
    plt.show()

if __name__ == "__main__":
    noise_analysis('./FFT/'+'p22.txt', fs=19200.0)