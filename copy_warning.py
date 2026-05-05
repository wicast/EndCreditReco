import csv
import os
import shutil

# 读取CSV文件并提取有问题的文件名（去重）
warning_files = set()
csv_path = r'd:\Projects\Python\EndCreditReco\ocr_warning.csv'

with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    # 打印列名用于调试
    print(f"CSV列名: {reader.fieldnames}")
    for row in reader:
        filename = row['filename']
        warning_files.add(filename)

print(f"找到 {len(warning_files)} 个有问题的文件")

# 源文件夹和目标文件夹
source_folder = r'd:\Projects\Python\EndCreditReco\信用商店'
target_folder = r'd:\Projects\Python\EndCreditReco\问题图片'
# target_folder = r'd:\Projects\Python\EndCreditReco\信用商店3'

# 创建目标文件夹
os.makedirs(target_folder, exist_ok=True)

# 复制文件
copied_count = 0
not_found_count = 0
not_found_files = []

for filename in warning_files:
    source_path = os.path.join(source_folder, filename)
    target_path = os.path.join(target_folder, filename)
    
    if os.path.exists(source_path):
        shutil.copy2(source_path, target_path)
        copied_count += 1
        print(f"已复制: {filename}")
    else:
        not_found_count += 1
        not_found_files.append(filename)
        print(f"未找到: {filename}")

print(f"\n复制完成！")
print(f"成功复制: {copied_count} 个文件")
print(f"未找到: {not_found_count} 个文件")

if not_found_files:
    print("\n未找到的文件列表:")
    for f in not_found_files:
        print(f"  - {f}")