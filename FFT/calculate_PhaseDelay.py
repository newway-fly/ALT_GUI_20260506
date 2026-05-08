# -*- coding: utf-8 -*-
import numpy as np
import matplotlib.pyplot as plt
import os

# =========================================================================
# [铁律] HIL (硬件在环) 绝对相位标定与双栖分析引擎
# 适用场景：MZM 偏离 NNQ 点 10%，同时下发 800Hz(I) 和 1200Hz(Q)。
# 架构特性：双栖架构。支持离线 TXT 诊断，也支持 PyQt5 GUI 内存数组直接调用。
# =========================================================================

def get_fft_mag_phase(data, t, N, freq, is_sine=True):
    """
    单频点数字正交解调核心引擎 (Single-Bin DFT)
    """
    w = 2.0 * np.pi * freq
    I_fft = np.sum(data * np.cos(w * t))
    Q_fft = np.sum(data * -np.sin(w * t))
    
    mag = np.sqrt(I_fft**2 + Q_fft**2) * (2.0 / N)
    raw_phase = np.degrees(np.arctan2(Q_fft, I_fft))
    
    # 物理极性对齐补偿
    if is_sine:
        nco_phase = raw_phase + 90.0
        if nco_phase > 180.0: nco_phase -= 360.0
    else:
        nco_phase = raw_phase
        
    return mag, nco_phase


def analyze_calibration_p22(p22_array, fs=19200.0, current_res_level=7, show_plot=True):
    """
    全频点相位提取与 C 代码生成器
    :param p22_array: 1D 浮点数列表/数组 (预期长度 1440)
    :param fs: 采样率 (默认 19.2kHz)
    :param current_res_level: 当前电阻档位，用于生成 C 语言代码时的矩阵索引
    :param show_plot: 是否使用 matplotlib 弹出阻塞图表 (GUI 自动调用时设为 False)
    :return: 包含 5 个特征频点幅值与相位的字典
    """
    data = np.array(p22_array)
    print(data)
    N = len(data)
    
    if N == 0:
        print("❌ 错误：输入数据为空！")
        return None

    if N != 1440:
        print(f"⚠️ 警告: 数据长度为 {N}，非标准 1440 点！频谱可能泄漏。")
        if N < 1440: return None

        data1 = data.replace('S1', '')
        data = data1.replace(',', ' ').split()

        data = data[:1440]
        N = 1440

    # 1. 严格复刻 MCU 底层的去直流与端点畸变抹平算法
    data = data - np.mean(data)
    data[0] = data[1] = data[2] = 0
    data[-1] = data[-2] = data[-3] = 0

    t = np.arange(N) / fs

    # 2. 提取 5 个核心物理频点的幅值与相位
    # 1f 与差频是正弦基底 (is_sine=True)
    mag_800,  ph_800  = get_fft_mag_phase(data, t, N, 800.0,  is_sine=True)
    mag_1200, ph_1200 = get_fft_mag_phase(data, t, N, 1200.0, is_sine=True)
    mag_400,  ph_400  = get_fft_mag_phase(data, t, N, 400.0,  is_sine=True)
    
    # 2f 是光学平方余弦基底 (is_sine=False)
    mag_1600, ph_1600 = get_fft_mag_phase(data, t, N, 1600.0, is_sine=False)
    mag_2400, ph_2400 = get_fft_mag_phase(data, t, N, 2400.0, is_sine=False) # 新增 2400Hz

    # 3. 输出直接可用的 C 语言结构
    print("\n" + "="*70)
    print(f"🚀 【硬件在环 (HIL) 绝对相位标定报告】")
    print(f"📌 当前提取环境: TIA 档位 = {current_res_level}, 采样点数 = {N}")
    print("="*70)
    
    print("\n[物理幅值探测] (检查是否成功泄露，若幅值 < 0.0001V 则相位不可信！)")
    print(f" - 800Hz  (I路 1f) : {mag_800:.6f} V")
    print(f" - 1200Hz (Q路 1f) : {mag_1200:.6f} V")
    print(f" - 1600Hz (I路 2f) : {mag_1600:.6f} V")
    print(f" - 2400Hz (Q路 2f) : {mag_2400:.6f} V")
    print(f" - 400Hz  (P路 Beat): {mag_400:.6f} V")

    print("\n" + "-"*70)
    print("📋 【请将以下代码直接复制到 410 main.c 的全局变量区中替换】")
    print("-"*70)
    
    print(f"// --- Mode A (IQP 联动) 补偿角更新: 档位 {current_res_level} ---")
    print(f"g_PhaseLUT_ModeA[{current_res_level}][0] = {ph_800:8.2f}f; // 800Hz (I)")
    print(f"g_PhaseLUT_ModeA[{current_res_level}][1] = {ph_1200:8.2f}f; // 1200Hz (Q)")
    print(f"g_PhaseLUT_ModeA[{current_res_level}][2] = {ph_400:8.2f}f; // 400Hz (P)")
    print("")
    print(f"// --- Mode B (单通道) 补偿角更新: 档位 {current_res_level} ---")
    print(f"g_PhaseLUT_ModeB[{current_res_level}][0] = {ph_800:8.2f}f; // 800Hz (1f)")
    print(f"g_PhaseLUT_ModeB[{current_res_level}][1] = {ph_1600:8.2f}f; // 1600Hz (I路 2f)")
    print(f"// 备注: 如果 Q 路使用单通道锁定，其 2f(2400Hz) 的物理补偿角为 {ph_2400:8.2f}f")
    print("="*70 + "\n")

    # 4. 可视化诊断 (仅在离线分析或明确要求时弹出)
    if show_plot:
        plt.rcParams['font.sans-serif'] = ['SimHei'] # 用来正常显示中文标签
        plt.rcParams['axes.unicode_minus'] = False   # 用来正常显示负号
        
        fft_y = np.abs(np.fft.fft(data)) * (2.0 / N)
        fft_x = np.fft.fftfreq(N, 1.0/fs)
        
        plt.figure(figsize=(12, 6))
        
        # 拓宽视野，显示 2800Hz 以内的正频半轴
        valid_idx = np.where((fft_x >= 0) & (fft_x <= 2800))
        plt.plot(fft_x[valid_idx], fft_y[valid_idx], 'k-', linewidth=1.2)
        
        # 打标特征频率
        markers = [
            (400, mag_400, 'orange', '400Hz(Beat)'),
            (800, mag_800, 'red', '800Hz(I)'),
            (1200, mag_1200, 'green', '1200Hz(Q)'),
            (1600, mag_1600, 'blue', '1600Hz(I_2f)'),
            (2400, mag_2400, 'purple', '2400Hz(Q_2f)') # 新增 2400Hz 画线
        ]
        
        for f, mag, col, label in markers:
            plt.axvline(x=f, color=col, linestyle='--', alpha=0.6, label=label)
            plt.text(f, mag, f" {mag:.5f}V", color=col, fontweight='bold', va='bottom')
            
        plt.title(f"HIL Phase Calibration Spectrum (Res_Level = {current_res_level})")
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Magnitude (V)")
        plt.grid(True, alpha=0.5)
        plt.legend(loc='upper right')
        
        # 将 X 轴界限扩展到 2800，以容纳 2400Hz
        plt.xlim(0, 2800)
        
        plt.tight_layout()
        plt.show()

    # 5. 将计算结果打包返回，供 GUI 上位机自动化流程无缝调用
    return {
        "800Hz":  {"mag": mag_800,  "phase": ph_800},
        "1200Hz": {"mag": mag_1200, "phase": ph_1200},
        "1600Hz": {"mag": mag_1600, "phase": ph_1600},
        "2400Hz": {"mag": mag_2400, "phase": ph_2400},
        "400Hz":  {"mag": mag_400,  "phase": ph_400},
    }

# =========================================================================
# 离线文件读取工具 (极简极速版)
# =========================================================================
def load_data_from_txt(filepath):
    """
    清洗并加载 TXT 数据。
    适配格式: 每行一个浮点数，末尾可能带逗号 (例如 "0.00711,")
    """
    data = []
    if not os.path.exists(filepath):
        print(f"❌ 错误：找不到文件 '{filepath}'。")
        return data

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                # 剥除首尾空白符（包括换行），剥除末尾的逗号
                cleaned_line = line.strip().rstrip(',')
                if cleaned_line:
                    try:
                        data.append(float(cleaned_line))
                    except ValueError:
                        pass # 滤除无法转为 float 的非数字行 (如表头等)
    except Exception as e:
        print(f"❌ 读取文件出错：{e}")
        
    return data

# =========================================================================
# 离线双击执行入口
# =========================================================================
if __name__ == "__main__":
    print("🚀 启动离线法医级相干采样相位提取器 (双路混频版)...")
    
    # 自动探测文件路径
    file_path = "p22_raw_data.txt" 
    if not os.path.exists(file_path):
        file_path = "./FFT/p22_raw_data.txt"
        
    print(f"正在读取文件: {file_path} ...")
    p22_raw_data = load_data_from_txt(file_path)
    
    if len(p22_raw_data) > 0:
        # 默认假设此时的档位是 *，离线执行时开启弹窗 (show_plot=True)
        analyze_calibration_p22(p22_raw_data, current_res_level='*', show_plot=True)
    else:
        print("❌ 无有效数据进行分析。请将带有逗号的浮点数保存到 txt 文件中。")