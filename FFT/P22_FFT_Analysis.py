import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq
import os

# ============================================================
# [铁律] 410工程专属相干采样分析脚本 (1440点版)
# 功能：特定频点侦测、绝对物理相位提取、NCO 补偿角直接生成
# 核心：使用矩形窗(无窗)保证 800Hz/1600Hz 的绝对数学精度
# ============================================================

def analyze_1440_coherent(filename='p22.txt', fs=19200.0, target_N=1440):
    # ---------------- 1. 数据加载与截断 ----------------
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

    if len(data) < target_N:
        print(f"❌ 错误: 数据长度 {len(data)} 小于目标要求 {target_N}")
        return
        
    # 强制截取前 1440 点，保证相干采样条件 (800Hz 恰好 60 个周期)
    data = data[:target_N]
    
    # ---------------- 2. 去直流与 FFT 计算 (相干法) ----------------
    dc_val = np.mean(data)
    ac_data = data - dc_val 
    
    ac_data[0] = 0
    ac_data[1] = 0
    ac_data[2] = 0

    # 【关键】：不加任何窗函数 (相当于矩形窗)，保证幅相不失真
    yf = fft(ac_data)
    xf = fftfreq(target_N, 1/fs)
    
    pos_mask = xf >= 0
    freqs = xf[pos_mask]
    mags = np.abs(yf[pos_mask]) * 2.0 / target_N  # 转换为实际电压幅值(V)
    phases = np.angle(yf[pos_mask], deg=True)     # 绝对物理相位 (Cosine为0度)

    # ---------------- 3. 精确频点数据提取 ----------------
    # 400Hz 已经在此列表中，自动会被提取并绘图
    target_freqs = [400, 800, 1200, 1600, 2000, 2400]
    results = {}
    
    # 频率分辨率 delta_f = 19200 / 1440 = 13.333Hz
    # 通过计算索引直接取值，不使用模糊搜索，防止旁瓣干扰
    for f in target_freqs:
        # 寻找距离目标频率最近的索引 bin
        idx = np.argmin(np.abs(freqs - f))
        real_f = freqs[idx]
        results[f] = {
            'mag_mV': mags[idx] * 1000.0,
            'phase': phases[idx],
            'real_f': real_f
        }

    # ---------------- 4. 打印专家级分析报告 ----------------
    print("\n" + "="*55)
    print(f"      410 工程 1440 点相干 FFT 与相位补偿报告")
    print("="*55)
    print(f"【频点能量分布 (Vpp提取)】")
    for f in target_freqs:
        mag = results[f]['mag_mV']
        ph = results[f]['phase']
        rf = results[f]['real_f']
        print(f"  > 目标 {f:4d}Hz (实际{rf:7.2f}Hz): 幅值 = {mag:7.3f} mV, 原始绝对相位 = {ph:7.2f}°")

    print(f"\n【410 NCO 寄存器补偿计算】")
    # 规则 1: 1f 信号 (800, 1200) C代码用 Sine 解调，需补偿 FFT相位 + 90度
    # 规则 2: 2f 信号 (1600)      C代码用 Cosine 解调，直接等于 FFT相位
    
    def calc_nco(base_phase, is_sine_demod):
            # 1f 信号因为 C 代码用 NCO.sin_val 解调，需要补充 90 度相位差
            shift = base_phase + 90.0 if is_sine_demod else base_phase
            
            # 【关键修正】: 将输出范围严格钳制在 [-180, +180] 之间，与 C 语言 atan2f 保持视觉一致
            shift = shift % 360.0
            if shift > 180.0:
                shift -= 360.0
            elif shift < -180.0:
                shift += 360.0
                
            return shift
        
    # --- [新增] 400Hz 的 NCO 计算 ---
    # 假设 400Hz 也是用 Sine 解调。如果 C 代码中 400Hz 用 Cosine，请把 True 改为 False
    nco_400  = calc_nco(results[400]['phase'], True) 
    
    nco_800  = calc_nco(results[800]['phase'], True)
    nco_1200 = calc_nco(results[1200]['phase'], True)
    nco_1600 = calc_nco(results[1600]['phase'], False)
    
    print(f" 💡 g_Nco_Phase_Deg  (0.5f/400Hz Sine) : {nco_400:6.2f} °") # 新增打印
    print(f" 💡 g_Nco1_Phase_Deg (I路/800Hz Sine)  : {nco_800:6.2f} °")
    print(f" 💡 g_Nco_Phase_Deg  (Q路/1200Hz Sine) : {nco_1200:6.2f} ° (若独立解调)")
    print(f" 💡 g_Nco2_Phase_Deg (2阶/1600Hz Cos)  : {nco_1600:6.2f} °")
    print("="*55 + "\n")

    # ---------------- 5. 针对性可视化 ----------------
    plt.figure(figsize=(12, 8))
    plt.rcParams['font.sans-serif'] = ['SimHei'] 
    plt.rcParams['axes.unicode_minus'] = False 

    # 子图1: 1440 点时域波形
    plt.subplot(2, 1, 1)
    t = np.arange(target_N) / fs
    plt.plot(t * 1000, ac_data * 1000, color='#1f77b4', linewidth=1.2)
    plt.title(f'1440 点交流信号时域波形 (去 DC)', fontsize=12)
    plt.xlabel('时间 (ms)')
    plt.ylabel('电压 (mV)')
    plt.grid(True, alpha=0.4)

    # 子图2: 对数坐标幅值谱，重点标注目标频点
    plt.subplot(2, 1, 2)
    mags_db = 20 * np.log10(mags + 1e-12)
    plt.plot(freqs, mags_db, color='#d62728', linewidth=1.0)
    
    colors = ['gray', 'blue', 'green', 'orange', 'purple', 'brown']
    for i, f in enumerate(target_freqs):
        plt.axvline(f, color=colors[i], linestyle='--', alpha=0.5)
        mag_db = 20 * np.log10(results[f]['mag_mV']/1000.0 + 1e-12)
        # 在顶部标记文字
        plt.text(f, mag_db + 2, f"{f}Hz", ha='center', va='bottom', color=colors[i], fontsize=10, fontweight='bold')
        # 画点
        plt.plot(results[f]['real_f'], mag_db, marker='o', markersize=6, color=colors[i])

    plt.title('特定频点相干检测幅值谱 (dBV)', fontsize=12)
    plt.xlabel('频率 (Hz)')
    plt.ylabel('幅值 (dBV)')
    plt.xlim(0, 3000)
    plt.ylim(np.max(mags_db) - 80, np.max(mags_db) + 15) # 动态显示范围，显示最大点往下 80dB
    plt.grid(True, which='both', alpha=0.3)

    plt.tight_layout()
    # 确保保存目录存在，防止报错
    os.makedirs('./FFT', exist_ok=True)
    plt.savefig('./FFT/P22_FFT_Analysis.png', dpi=300)
    plt.show()

if __name__ == "__main__":
    # analyze_1440_coherent('./FFT/p22.txt', fs=19200.0, target_N=1440)
    analyze_1440_coherent('./FFT/p22.txt', fs=19200.0, target_N=1440)