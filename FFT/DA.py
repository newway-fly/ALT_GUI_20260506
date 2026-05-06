import numpy as np
import matplotlib.pyplot as plt

# 读取数据，添加异常处理
try:
    data = np.loadtxt('./FFT/DA.txt')
except FileNotFoundError:
    print("错误：未找到文件 './FFT/DA.txt'，请检查路径。")
    exit()

# 自动计算数据个数
N = len(data)
print(f"数据个数: {N}")

# 计算最大值、最小值、差值及其索引
max_val = np.max(data)
min_val = np.min(data)
diff = max_val - min_val
max_idx = np.argmax(data)   # 最大值所在索引
min_idx = np.argmin(data)   # 最小值所在索引

print(f"最大值: {max_val:.4f} 位于索引 {max_idx}")
print(f"最小值: {min_val:.4f} 位于索引 {min_idx}")
print(f"差值 (max - min): {diff:.4f}")

# 生成x坐标
x = np.arange(N)

# 绘图
plt.figure(figsize=(8, 5))
plt.plot(x, data, marker='o', linestyle='-', markersize=3, label='数据曲线')

# 标注最大值和最小值点
plt.plot(max_idx, max_val, 'ro', markersize=8, label=f'最大值: {max_val:.4f} @ index {max_idx}')
plt.plot(min_idx, min_val, 'go', markersize=8, label=f'最小值: {min_val:.4f} @ index {min_idx}')

# 添加标题和标签
plt.title(f"DA Data Plot (差值 = {diff:.4f})")
plt.xlabel("Index")
plt.ylabel("Value")
plt.grid(True)
plt.legend()  # 显示图例

# 自动调整布局并保存图片
plt.tight_layout()
plt.savefig("DA_plot.png", dpi=300)

# 显示图形
plt.show() 