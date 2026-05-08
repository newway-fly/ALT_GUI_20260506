import numpy as np
import matplotlib.pyplot as plt
import os

filename = "p22.txt"

import os

script_dir = os.path.dirname(os.path.abspath(__file__))
filename = os.path.join(script_dir, "p22.txt")

print("读取文件:", filename)

if not os.path.exists(filename):
    raise FileNotFoundError(f"未找到文件: {filename}")

# 2️⃣ 读取并清洗数据
data = []
with open(filename, "r") as f:
    for line_num, line in enumerate(f):
        parts = line.strip().split(",")

        # 跳过异常行（列数不对）
        if len(parts) < 2:
            continue

        try:
            # 只取前两列（时间 + 信号）
            row = [float(parts[0]), float(parts[1])]
            data.append(row)
        except:
            # 跳过无法转换的行
            continue

data = np.array(data)

if data.shape[0] == 0:
    raise ValueError("没有有效数据，检查文件格式")

# 3️⃣ 拆分数据
t = data[:, 0]
signal = data[:, 1]

# 4️⃣ 去直流分量（推荐）
signal = signal - np.mean(signal)

# 5️⃣ FFT
N = len(signal)
dt = t[1] - t[0]  # 采样间隔
fft_vals = np.fft.fft(signal)
freqs = np.fft.fftfreq(N, dt)

# 只取正频率
mask = freqs > 0
freqs = freqs[mask]
fft_vals = np.abs(fft_vals[mask])

# 6️⃣ 找主频
main_freq = freqs[np.argmax(fft_vals)]
print(f"主频率: {main_freq:.3f} Hz")

# 7️⃣ 画图
plt.figure(figsize=(10, 5))
plt.plot(freqs, fft_vals)
plt.xlabel("Frequency (Hz)")
plt.ylabel("Amplitude")
plt.title("FFT Spectrum")
plt.grid()

# 标出主频
plt.axvline(main_freq, linestyle='--')
plt.text(main_freq, max(fft_vals)*0.8, f"{main_freq:.2f} Hz")

plt.show()