import numpy as np
import matplotlib.pyplot as plt

def read_data(filepath):
    """
    读取文本文件中的数值数据，返回一维 numpy 数组。
    兼容每行末尾带逗号、空格分隔、多列混合等情况。
    """
    values = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:          # 跳过空行
                    continue
                # 如果行尾有逗号，去掉它
                if line.endswith(','):
                    line = line[:-1]
                # 按空白或逗号分割（因为可能一行有多个数值）
                parts = line.replace(',', ' ').split()
                for part in parts:
                    try:
                        values.append(float(part))
                    except ValueError:
                        print(f"警告：忽略无法解析的部分 '{part}'")
        return np.array(values)
    except Exception as e:
        print(f"读取文件失败: {e}")
        exit(1)

def plot_groups(data):
    point =40
    num = 12
    """按照 20*12, 20*12, 20, 20*12, 20*12, 20 的顺序分割数据并绘制子图"""
    len_group1 = point * num          # 240
    len_group2 = point * num          # 240
    len_group3 = point               # 20
    len_group4 = point * num          # 240
    len_group5 = point * num          # 240
    len_group6 = point               # 20
    expected_len = len_group1 + len_group2 + len_group3 + len_group4 + len_group5 + len_group6
    index1=len_group1
    index2=index1+len_group2
    index3=index2+len_group3
    index4=index3+len_group4
    index5=index4+len_group5
    index6=index5+len_group6


    if len(data) != expected_len:
        print(f"数据长度应为 {expected_len}，实际为 {len(data)}。请检查文件内容。")
        exit(1)

    # 分割数据
    part1 = data[0:index1].reshape(point, num)
    part2 = data[index1:index2].reshape(point, num)
    part3 = data[index2:index3]
    part4 = data[index3:index4].reshape(point, num)
    part5 = data[index4:index5].reshape(point, num)
    part6 = data[index5:index6]

    parts = [part1, part2, part3, part4, part5, part6]

    # 创建 2 行 3 列的子图
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    axes = axes.flatten()

    x_12 = np.arange(num)
    x_20 = np.arange(point)

    for idx, ax in enumerate(axes):
        part = parts[idx]

        if idx in [0, 1, 3, 4]:   # 20*12 组
            for row in range(point):
                ax.plot(x_12, part[row], marker='o', markersize=3, linewidth=1.5)
            ax.set_title(f'Group {idx+1}: {point} curves × {num} points')
            ax.set_xlabel(f'Point index ({1}-{num})')
            ax.set_ylabel('Value')
        else:                      # 20 组
            ax.plot(x_20, part, marker='o', markersize=4, linewidth=1.5)
            ax.set_title(f'Group {idx+1}: 1 curve × {point} points')
            ax.set_xlabel(f'Point index ({1}-{point})')
            ax.set_ylabel('Value')

        ax.grid(True)

        # 统计信息
        max_val = np.max(part)
        min_val = np.min(part)
        diff = max_val - min_val

        ax.text(0.02, 0.98,
                f'max = {max_val:.4f}\nmin = {min_val:.4f}\ndiff = {diff:.4f}',
                transform=ax.transAxes,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    plt.savefig('group_plots.png', dpi=300)
    plt.show()

if __name__ == "__main__":
    # 请修改为您的实际文件路径
    filepath = './FFT/NNQ_Scan_All_Curve.txt'   # 例如 './FFT/NNQ_Scan_All_Curve.txt'
    data = read_data(filepath)
    plot_groups(data)