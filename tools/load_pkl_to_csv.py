import pandas as pd
import os

def convert_pkl_to_csv(pkl_folder, csv_folder=None):
    """
    批量将文件夹中的 .pkl 文件转换为 .csv 文件（保持格式不变）
    
    参数:
    pkl_folder (str): 输入的 .pkl 文件所在文件夹路径（相对或绝对路径）
    csv_folder (str): 输出的 .csv 文件保存文件夹路径，默认为 None 时与输入文件夹相同
    """
    # 处理路径（转为绝对路径）
    pkl_folder = os.path.abspath(pkl_folder)
    if csv_folder is None:
        csv_folder = pkl_folder  # 输出路径与输入路径一致
    else:
        csv_folder = os.path.abspath(csv_folder)
        os.makedirs(csv_folder, exist_ok=True)  # 创建输出文件夹（若不存在）

    # 遍历文件夹内所有 .pkl 文件
    for filename in os.listdir(pkl_folder):
        if filename.endswith(".pkl"):
            pkl_path = os.path.join(pkl_folder, filename)
            csv_name = os.path.splitext(filename)[0] + ".csv"  # 生成对应的 csv 文件名
            csv_path = os.path.join(csv_folder, csv_name)
            
            try:
                # 读取 pkl 文件
                df = pd.read_pickle(pkl_path)
                # 保存为 csv 文件（保留原始格式，包括列名、数据类型等）
                df.to_csv(csv_path, index=False)  # index=False 避免生成额外索引列
                print(f"已转换：{pkl_path} -> {csv_path}")
            except Exception as e:
                print(f"转换失败：{pkl_path}，错误：{str(e)}")

# 使用示例
if __name__ == "__main__":
    # 输入文件夹路径（相对路径：当前脚本所在目录下的 ./股指期货市场数据（近三年））
    pkl_folder = "./"
    # 输出文件夹路径（可选，默认为同输入文件夹）
    csv_folder = "./"  # 若需单独保存可指定新路径
    
    convert_pkl_to_csv(pkl_folder, csv_folder)