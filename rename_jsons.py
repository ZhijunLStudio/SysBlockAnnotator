import os
import shutil
import argparse

def rename_json_files(source_dir, dest_dir):
    """
    遍历源目录，将文件名中包含'_annotated_pred.json'的文件
    重命名为'.json'并复制到目标目录。

    :param source_dir: 包含原始JSON文件的文件夹路径。
    :param dest_dir: 用于存放重命名后JSON文件的新文件夹路径。
    """
    # 定义要查找和替换的后缀
    suffix_to_remove = '_pred.json'
    new_suffix = '.json'

    # 检查源目录是否存在
    if not os.path.isdir(source_dir):
        print(f"错误：源目录 '{source_dir}' 不存在。")
        return

    # 创建目标目录，如果它不存在的话
    os.makedirs(dest_dir, exist_ok=True)
    print(f"将把重命名后的文件保存在: '{dest_dir}'")

    renamed_count = 0
    # 遍历源目录中的所有文件
    for filename in os.listdir(source_dir):
        if filename.endswith(suffix_to_remove):
            # 构建新的文件名
            new_filename = filename.replace(suffix_to_remove, new_suffix)
            
            # 构建完整的文件路径
            old_filepath = os.path.join(source_dir, filename)
            new_filepath = os.path.join(dest_dir, new_filename)
            
            # 复制并重命名文件
            shutil.copy2(old_filepath, new_filepath)
            print(f"已处理: '{filename}' -> '{new_filename}'")
            renamed_count += 1
            
    print(f"\n处理完成！总共重命名并复制了 {renamed_count} 个文件。")

if __name__ == '__main__':
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(description="批量重命名JSON文件，去除'_annotated_pred'后缀。")
    parser.add_argument("source_directory", help="包含原始JSON文件的文件夹路径。")
    parser.add_argument("destination_directory", help="用于存放重命名后文件的新文件夹路径。")
    
    args = parser.parse_args()
    
    rename_json_files(args.source_directory, args.destination_directory)