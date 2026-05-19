import csv
from collections import defaultdict

def check_discount_counts():
    total_refreshes = 0
    current_file = None
    discount_counts_in_refresh = defaultdict(int)
    low_discount_refreshes = []
    
    with open(r'd:\Projects\Python\EndCreditReco\ocr_result.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row['filename']
            discount = row['discount']
            
            if filename != current_file:
                if current_file is not None:
                    total_refreshes += 1
                    total_discounts = sum(discount_counts_in_refresh.values())
                    if total_discounts < 2:
                        low_discount_refreshes.append((current_file, total_discounts, dict(discount_counts_in_refresh)))
                current_file = filename
                discount_counts_in_refresh = defaultdict(int)
            
            if discount != '0':
                discount_counts_in_refresh[discount] += 1
    
    if current_file is not None:
        total_refreshes += 1
        total_discounts = sum(discount_counts_in_refresh.values())
        if total_discounts < 3:
            low_discount_refreshes.append((current_file, total_discounts, dict(discount_counts_in_refresh)))

    print(f'总刷新次数: {total_refreshes}')
    print(f'折扣数少于3个的刷新次数: {len(low_discount_refreshes)}\n')
    
    if low_discount_refreshes:
        print('折扣数少于3个的刷新记录:')
        print('=' * 60)
        for filename, total, counts in low_discount_refreshes:
            disc_str = ', '.join([f'{k}:{v}' for k, v in sorted(counts.items())])
            print(f'文件: {filename}')
            print(f'  有效折扣数: {total}个')
            print(f'  折扣详情: {disc_str}')
            print()
    else:
        print('未发现折扣数少于3个的刷新记录')

if __name__ == '__main__':
    check_discount_counts()