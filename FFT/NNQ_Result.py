import matplotlib.pyplot as plt
import re

def parse_data(text):
    """
    逐行解析文本，提取块名和对应的数据。
    每行可能带有时间戳，忽略。
    返回字典 {块名: (频率列表, 数值列表)}
    """
    lines = text.splitlines()
    blocks = {}
    current_block = None
    freqs = []
    values = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 检测块开始
        if '----BEGIN_NNQ_' in line:
            match = re.search(r'----BEGIN_NNQ_([A-Z]+)----', line)
            if match:
                current_block = match.group(1)
                freqs = []
                values = []
            continue

        # 检测块结束
        if current_block and '----END_NNQ_' in line:
            if current_block in line:  # 确保是当前块的结束
                blocks[current_block] = (freqs, values)
                current_block = None
                freqs = []
                values = []
            continue

        # 如果在块内，处理数据行
        if current_block:
            # 提取频率和数值（忽略行首时间戳）
            match = re.search(r'(\d+)\s*,\s*([-+]?\d*\.?\d+)', line)
            if match:
                try:
                    freq = int(match.group(1))
                    val = float(match.group(2))
                    freqs.append(freq)
                    values.append(val)
                except ValueError:
                    pass  # 忽略无效行

    return blocks

def main():
    filename = "./FFT/NNQ_Result.txt"
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data_text = f.read()
    except FileNotFoundError:
        print(f"错误：找不到文件 {filename}，请检查路径是否正确。")
        return

    blocks = parse_data(data_text)

    if not blocks:
        print("未找到任何有效数据块。请检查文件内容是否包含正确的 BEGIN/END 标记。")
        print("文件开头内容预览：")
        print(data_text[:200])
        return

    # 打印找到的块名和数据点数
    for name, (f, v) in blocks.items():
        print(f"找到块 {name}，数据点数量：{len(f)}")

    # 定义子图布局：2行3列
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    axes = axes.flatten()  # 将2x3的axes数组展平为6个元素的列表，便于索引

    # 按照期望的顺序排列块名（可自行调整）
    block_order = ['XQ', 'XI', 'XP', 'YQ', 'YI', 'YP']
    for i, name in enumerate(block_order):
        if name in blocks:
            freqs, values = blocks[name]
            ax = axes[i]
            ax.plot(freqs, values, marker='o', linestyle='-')
            ax.set_title(f'NNQ_{name}')
            ax.set_xlabel('Frequency')
            ax.set_ylabel('Value')
            ax.grid(True)
        else:
            # 如果某个块缺失，在对应子图中显示提示
            axes[i].text(0.5, 0.5, f'No data for {name}', ha='center', va='center')
            axes[i].set_title(f'NNQ_{name}')

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()