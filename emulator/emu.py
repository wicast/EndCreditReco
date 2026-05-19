import csv
import random
from collections import defaultdict

DISCOUNTS = [0, 25, 50, 75, 95, 99]  # 折扣类型
TOTAL_CSV = '总数.csv'
DISTRIBUTION_CSV = '分布.csv'

class ShopEmulator:
    def __init__(self):
        self.item_counts = {}  # 物品总数
        self.item_probabilities = {}  # 物品出现概率
        self.discount_distributions = {}  # 折扣分布
        self._load_data()
    
    def _load_data(self):
        # 读取总数.csv
        with open(TOTAL_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    item_name = row[0].strip()
                    count = int(row[1].strip())
                    self.item_counts[item_name] = count
        
        # 计算物品出现概率
        total = sum(self.item_counts.values())
        for item, count in self.item_counts.items():
            self.item_probabilities[item] = count / total
        
        # 读取分布.csv
        with open(DISTRIBUTION_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 7:
                    item_name = row[0].strip()
                    counts = [int(row[i].strip()) for i in range(1, 7)]
                    self.discount_distributions[item_name] = counts
        
        # 确保折金票的分布存在（用于其他物品）
        if '折金票' not in self.discount_distributions:
            raise ValueError("分布.csv中缺少折金票的折扣分布数据")
    
    def _get_discount(self, item_name):
        """根据物品名称获取折扣"""
        # 嵌晶玉和武库配额使用自己的分布
        if item_name in ['嵌晶玉', '武库配额'] and item_name in self.discount_distributions:
            counts = self.discount_distributions[item_name]
        else:
            # 其他物品使用折金票的分布
            counts = self.discount_distributions['折金票']
        
        total = sum(counts)
        if total == 0:
            return 0  # 默认返回0%折扣
        
        # 根据分布随机选择折扣
        rand = random.random() * total
        cumulative = 0
        for i, count in enumerate(counts):
            cumulative += count
            if rand < cumulative:
                return DISCOUNTS[i]
        return DISCOUNTS[-1]
    
    def refresh(self, num_items=10):
        """执行一次商店刷新，返回刷新结果列表，每次固定num_items个商品"""
        result = []
        items_list = list(self.item_counts.keys())
        probs_list = [self.item_probabilities[item] for item in items_list]
        
        # 记录已添加的物品（用于去重）
        added_items = set()
        # 标记是否已添加特殊物品（武库配额或嵌晶玉）
        has_special = False
        
        # 循环直到收集到指定数量的物品
        while len(result) < num_items:
            # 随机选择物品（使用加权随机）
            selected_item = random.choices(items_list, weights=probs_list)[0]
            
            # 处理武库配额和嵌晶玉的特殊情况
            if selected_item == '武库配额':
                # 如果已经有特殊物品或已添加过，则跳过
                if has_special or selected_item in added_items:
                    continue
                discount = self._get_discount('武库配额')
                result.append((selected_item, discount))
                added_items.add(selected_item)
                has_special = True
            elif selected_item == '嵌晶玉':
                # 如果已经有特殊物品或已添加过，则跳过
                if has_special or selected_item in added_items:
                    continue
                discount = self._get_discount('嵌晶玉')
                result.append((selected_item, discount))
                added_items.add(selected_item)
                has_special = True
            else:
                # 其他物品正常处理（不允许重复）
                if selected_item in added_items:
                    continue
                discount = self._get_discount(selected_item)
                result.append((selected_item, discount))
                added_items.add(selected_item)
        
        return result
    
    def simulate_multiple(self, times=10):
        """模拟多次刷新"""
        results = []
        for _ in range(times):
            results.append(self.refresh())
        return results

def main():
    emulator = ShopEmulator()
    
    # 执行一次刷新并输出结果
    result = emulator.refresh()
    print("商店刷新结果：")
    for item, discount in result:
        print(f"  {item} - 折扣: {discount}%")

if __name__ == '__main__':
    main()
