import csv
from collections import defaultdict

total_refreshes = 0
target_appearances = 0
current_file = None
target_in_current = False
discount_distribution = defaultdict(int)

target_item = '武库配额'
target_item = '嵌晶玉'
target_item = '中级作战记录'
# target_item = '折金票'

with open(r'd:\Projects\Python\EndCreditReco\ocr_result.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        filename = row['filename']
        item = row['item']
        discount = row['discount']
        
        if filename != current_file:
            if current_file is not None:
                total_refreshes += 1
                if target_in_current:
                    target_appearances += 1
            current_file = filename
            target_in_current = False
        
        if item == target_item:
            target_in_current = True
            discount_distribution[discount] += 1
    
    if current_file is not None:
        total_refreshes += 1
        if target_in_current:
            target_appearances += 1

print(f'总刷新次数: {total_refreshes}')
print(f'{target_item}出现次数: {target_appearances}')
print(f'{target_item}出现概率: {target_appearances / total_refreshes * 100:.2f}%')

print(f'\n{target_item}折扣分布:')
for discount, count in sorted(discount_distribution.items()):
    percentage = count / target_appearances * 100 if target_appearances > 0 else 0
    print(f'  {discount}: {count}次 ({percentage:.2f}%)')
