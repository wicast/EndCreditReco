import os
import csv
import glob
from paddleocr import PaddleOCR

# 配置路径
image_folder = r"extra"
white_list_path = r"target.txt"
replace_rules_path = r"replace.txt"
output_csv = r"ocr_result.csv"
warning_csv = r"ocr_warning.csv"
warning_count_txt = r"ocr_warning_stats.txt"
    


def load_white_list(filepath):
    """加载白名单文件"""
    white_list = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                white_list.append(line)
    return white_list

def load_replace_rules(filepath):
    """加载替换规则文件"""
    replace_rules = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split(' ', 1)  # 按第一个空格分割
                if len(parts) == 2:
                    wrong_text, correct_text = parts
                    replace_rules[wrong_text] = correct_text
    return replace_rules

def apply_replace_rules(text, replace_rules):
    """应用替换规则"""
    for wrong_text, correct_text in replace_rules.items():
        if text == wrong_text:
            text = text.replace(wrong_text, correct_text)
    return text

def process_image(ocr, image_path, white_list, replace_rules=None):
    """处理单张图片，返回匹配的白名单文字和折扣"""
    try:
        result = ocr.predict(image_path)
        rec_texts = []
        
        # 从结果中提取rec_texts
        for res in result:
            rec_texts.extend(res['rec_texts'])
        
        # 应用替换规则，修正OCR识别错误
        corrected_texts = []
        for text in rec_texts:
            if replace_rules:
                corrected_text = apply_replace_rules(text, replace_rules)
            else:
                corrected_text = text
            corrected_texts.append(corrected_text)
        
        # 提取白名单匹配项
        matched_items = []
        for text in corrected_texts:
            for item in white_list:
                if item == text:
                    matched_items.append(item)
                    break
        
        # 提取折扣比例（包含%的文字）
        discounts = []
        for text in rec_texts:
            if '%' in text:
                discounts.append(text)
        
        # 检查matched_items数量是否为10
        warning = ""
        if len(matched_items) != 10:
            warning = f"警告：matched_items数量为 {len(matched_items)}，预期为10"
            print(warning)
            
            # 将res保存为JSON到问题图片文件夹
            output_dir = "问题图片"
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.splitext(os.path.basename(image_path))[0]
            for idx, res in enumerate(result):
                res.save_to_json(output_dir)
        
        return matched_items, discounts, warning
    except Exception as e:
        print(f"处理图片 {image_path} 时出错: {e}")
        return [], [], ""

def match_items_with_discounts(matched_items, discounts):
    """匹配白名单项和折扣"""
    results = []
    
    # 如果没有折扣，所有匹配项折扣为0
    if not discounts:
        for item in matched_items:
            results.append({"item": item, "discount": "0"})
        return results
    
    # 尝试根据顺序匹配
    # 假设折扣和物品是按顺序排列的
    discount_index = 0
    for item in matched_items:
        if discount_index < len(discounts):
            results.append({"item": item, "discount": discounts[discount_index]})
            discount_index += 1
        else:
            results.append({"item": item, "discount": "0"})
    
    return results

def main():

    # 加载白名单
    white_list = load_white_list(white_list_path)
    print(f"白名单加载完成，共 {len(white_list)} 项")
    
    # 加载替换规则
    replace_rules = load_replace_rules(replace_rules_path)
    print(f"替换规则加载完成，共 {len(replace_rules)} 条")
    
    # 初始化OCR
    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping = True,
        # device="gpu",
        use_textline_orientation=False,
        engine="transformers",
    )
    print("OCR引擎初始化完成")
    
    # 获取所有图片文件
    image_patterns = ["*.jpg", "*.png", "*.jpeg"]
    image_files = []
    for pattern in image_patterns:
        image_files.extend(glob.glob(os.path.join(image_folder, pattern)))
    
    # image_files.sort()
    print(f"找到 {len(image_files)} 张图片")
    
    # 处理所有图片并收集结果
    all_results = []
    warning_results = []
    warning_count = 0
    file_count = 0
    for image_path in image_files:
        print(f"正在处理: {os.path.basename(image_path)}, 已处理 {file_count} 张图片")
        matched_items, discounts, warning = process_image(ocr, image_path, white_list, replace_rules)
        if warning:
            warning_count += 1
        
        if matched_items:
            matched_results = match_items_with_discounts(matched_items, discounts)
            for result in matched_results:
                result_dict = {
                    "filename": os.path.basename(image_path),
                    "item": result["item"],
                    "discount": result["discount"]
                }
                if warning:
                    result_dict["warning"] = warning
                    warning_results.append(result_dict)
                else:
                    all_results.append(result_dict)
        else:
            # 如果没有匹配到白名单项，仍记录文件名
            result_dict = {
                "filename": os.path.basename(image_path),
                "item": "",
                "discount": "0"
            }
            if warning:
                result_dict["warning"] = warning
                warning_results.append(result_dict)
            else:
                all_results.append(result_dict)
        file_count += 1
    
    # 写入正常结果CSV
    with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "item", "discount"])
        writer.writeheader()
        writer.writerows(all_results)
    
    print(f"结果已保存到 {output_csv}")
    
    # 写入警告结果CSV
    if warning_results:
        with open(warning_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["filename", "item", "discount", "warning"])
            writer.writeheader()
            writer.writerows(warning_results)
        
        print(f"警告结果已保存到 {warning_csv}")

    with open(warning_count_txt, 'w', encoding='utf-8-sig') as f:
        f.write(f"警告数量: {warning_count}")
        print(f"警告数量: {warning_count}")

if __name__ == "__main__":
    main()