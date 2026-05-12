import os
import csv
import glob
import re
import shutil
from paddleocr import PaddleOCR
from rapidfuzz import fuzz, process
from file_date_detect import get_image_datetime, load_csv_submission_times

# 配置路径
image_folder = r"downloaded_images1"
white_list_path = r"target.txt"
replace_rules_path = r"replace.txt"
output_csv = r"ocr_result.csv"
warning_csv = r"ocr_warning.csv"
warning_count_txt = r"ocr_warning_stats.txt"
csv_path = r"问卷_问卷.csv"

clean_warning = True

# 用正则表达式尝试模糊匹配ocr识别错误
fuzzy_regex = [
    (r'[衫韧初级矢口知认人].*[知认人载体]', '初级认知载体'),
    (r'中.*[记录]', '中级作战记录'),
    (r'[衫韧初级].*[记录]', '初级作战记录'),
    (r'[重型].*[具]', '重型强固模具'),
    (r'[武器检查试赋].*[装置]', '武器检查装置'),
    (r'[武器检查试赋].*[单元]', '武器检查单元'),
    (r'[圆盘].*[目组]', '协议圆盘组'),
]

# 模糊匹配的候选名称列表（将从 target.txt 加载）
fuzzy_candidates = []


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

def extract_extra_info(rec_texts):
    """从识别文本中提取UID、剩余刷新次数和库存刷新时间"""
    uid = ""
    remaining_refresh = ""
    refresh_hour = ""

    uid_pattern = re.compile(r'U[1I]D[：:]?\s*(\d+)', re.IGNORECASE)
    remaining_pattern = re.compile(r'剩余次数[：:]\s*(\d+)/(\d+)')
    countdown_pattern = re.compile(r'库存刷新倒计时[：:]\s*(\d+)小时(\d+)分钟')
    countdown_hour_chinese_pattern = re.compile(r'库存刷新倒计时[：:]\s*(\d+)时(\d+)分钟')
    countdown_minutes_only_pattern = re.compile(r'库存刷新倒计时[：:]\s*(\d+)分钟')
    refresh_exhausted_pattern = re.compile(r'今日刷新次数已用尽', re.IGNORECASE)

    for i, text in enumerate(rec_texts):
        text = text.strip()
        
        if not uid:
            m = uid_pattern.search(text)
            if m:
                uid = m.group(1)

        if not remaining_refresh:
            m = remaining_pattern.search(text)
            if m:
                remaining_refresh = f"{m.group(1)}/{m.group(2)}"
            elif refresh_exhausted_pattern.search(text):
                remaining_refresh = "0/4"

        if not refresh_hour:
            m = countdown_pattern.search(text)
            if m:
                refresh_hour = m.group(1)
            else:
                m = countdown_hour_chinese_pattern.search(text)
                if m:
                    refresh_hour = m.group(1)
                else:
                    m = countdown_minutes_only_pattern.search(text)
                    if m:
                        refresh_hour = "0"

        if not uid:
            m = process.extractOne(text, ["UID", "U1D"], scorer=fuzz.ratio, score_cutoff=60)
            if m:
                uid_match = re.search(r'(\d{7,})', text)
                if uid_match:
                    uid = uid_match.group(1)

        if not remaining_refresh:
            m = process.extractOne(text, ["剩余次数", "今日刷新次数已用尽"], scorer=fuzz.ratio, score_cutoff=60)
            if m:
                if "用尽" in m[0] or "已用" in text:
                    remaining_refresh = "0/4"
                else:
                    remaining_match = re.search(r'(\d+)/(\d+)', text)
                    if remaining_match:
                        remaining_refresh = f"{remaining_match.group(1)}/{remaining_match.group(2)}"

        if not refresh_hour:
            m = process.extractOne(text, ["库存刷新倒计时"], scorer=fuzz.ratio, score_cutoff=60)
            if m:
                hour_match = re.search(r'(\d+)小时', text)
                if not hour_match:
                    hour_match = re.search(r'(\d+)时', text)
                if hour_match:
                    refresh_hour = hour_match.group(1)
                else:
                    minutes_match = re.search(r'(\d+)分钟', text)
                    if minutes_match:
                        refresh_hour = "0"

        if not refresh_hour and i + 1 < len(rec_texts):
            combined_text = text + rec_texts[i + 1]
            m = countdown_pattern.search(combined_text)
            if m:
                refresh_hour = m.group(1)
            else:
                m = countdown_hour_chinese_pattern.search(combined_text)
                if m:
                    refresh_hour = m.group(1)

    return uid, remaining_refresh, refresh_hour

def process_image(ocr, image_path, white_list, replace_rules=None):
    """处理单张图片，返回匹配的白名单文字、折扣和额外信息"""
    try:
        from PIL import Image

        img = Image.open(image_path)
        img_height = img.height
        img.close()

        result = ocr.predict(image_path)
        rec_texts = []
        rec_boxes = []

        for res in result:
            rec_texts.extend(res['rec_texts'])
            rec_boxes.extend(res['rec_boxes'])

        uid, remaining_refresh, refresh_hour = extract_extra_info(rec_texts)
        
        # 提取白名单匹配项及其位置信息
        matched_items = []
        matched_boxes = []
        for idx, text in enumerate(rec_texts):
            white_list_found = False
            for white_item in white_list:
                if white_item == text:
                    matched_items.append(white_item)
                    matched_boxes.append(rec_boxes[idx])
                    white_list_found = True
                    break

            # 如果不在白名单中，尝试模糊匹配
            if not white_list_found:
                fuzzy_found = False
                # 先尝试正则表达式匹配
                for reg, correct_name in fuzzy_regex:
                    if re.search(reg, text):
                        matched_items.append(correct_name)
                        matched_boxes.append(rec_boxes[idx])
                        fuzzy_found = True
                        break
                
                # 如果正则匹配失败，再尝试 rapidfuzz 相似度匹配
                if not fuzzy_found:
                    m = process.extractOne(text, fuzzy_candidates, scorer=fuzz.ratio)
                    if m:
                        best_match, score, _ = m
                        if score >= 68.0:
                            matched_items.append(best_match)
                            matched_boxes.append(rec_boxes[idx])
        
        # 提取折扣比例及其位置信息
        discounts = []
        discount_boxes = []
        for idx, text in enumerate(rec_texts):
            if '%' in text:
                discounts.append(text)
                discount_boxes.append(rec_boxes[idx])
        
        # 根据空间位置匹配折扣到物品
        # 折扣应该在物品的右上方，且不超过图片高度40%的距离
        item_discounts = []
        for item_box in matched_boxes:
            item_x_center = (item_box[0] + item_box[2]) / 2
            item_y_center = (item_box[1] + item_box[3]) / 2
            
            best_discount = "0"
            best_score = float('inf')
            max_up_distance = img_height * 0.4
            
            for discount, disc_box in zip(discounts, discount_boxes):
                disc_x_center = (disc_box[0] + disc_box[2]) / 2
                disc_y_center = (disc_box[1] + disc_box[3]) / 2
                
                # 计算向上距离
                up_distance = item_y_center - disc_y_center
                
                # 折扣应该在物品右上方，且向上距离不超过图片高度40%
                # x更大（偏右），y更小（偏上）
                if disc_x_center > item_x_center and disc_y_center < item_y_center and up_distance <= max_up_distance:
                    # 计算距离，越近越好
                    score = abs(disc_x_center - item_x_center) + abs(disc_y_center - item_y_center)
                    if score < best_score:
                        best_score = score
                        best_discount = discount
            
            item_discounts.append(best_discount)
        
        # 检查matched_items数量是否为10以及额外信息是否完整
        warning = ""
        missing_fields = []
        if len(matched_items) != 10:
            missing_fields.append(f"matched_items数量为 {len(matched_items)}（预期为10）")
        if not uid:
            missing_fields.append("缺少UID")
        if not remaining_refresh:
            missing_fields.append("缺少剩余刷新次数")
        if not refresh_hour:
            missing_fields.append("缺少库存刷新时间")
        
        if missing_fields:
            warning = "警告：" + "；".join(missing_fields)
            print(warning)
            
            # 将识别结果保存为JSON到问题图片文件夹
            output_dir = "问题图片"
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.splitext(os.path.basename(image_path))[0]
            
            # 构建输出JSON内容
            output_data = {
                "matched_items": matched_items,
                "rec_texts": rec_texts,
                "item_count": len(matched_items),
                "uid": uid,
                "remaining_refresh": remaining_refresh,
                "refresh_hour": refresh_hour
            }
            
            # 保存JSON文件
            json_path = os.path.join(output_dir, f"{filename}_result.json")
            import json
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            # 使用软连接替代拷贝图片
            dest_image_path = os.path.join(output_dir, os.path.basename(image_path))
            if os.path.exists(dest_image_path) or os.path.islink(dest_image_path):
                os.remove(dest_image_path)
            os.symlink(os.path.abspath(image_path), dest_image_path)
        
        return matched_items, item_discounts, warning, uid, remaining_refresh, refresh_hour
    except Exception as e:
        print(f"处理图片 {image_path} 时出错: {e}")
        return [], [], "", "", "", ""

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

    # 如果clean_warning为True，清理问题图片文件夹
    if clean_warning:
        warning_dir = "问题图片"
        if os.path.exists(warning_dir):
            for filename in os.listdir(warning_dir):
                file_path = os.path.join(warning_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"删除文件 {file_path} 时出错: {e}")
            print("问题图片文件夹已清理")

    # 加载白名单
    white_list = load_white_list(white_list_path)
    print(f"白名单加载完成，共 {len(white_list)} 项")
    
    # 模糊匹配候选列表也从 target.txt 加载
    global fuzzy_candidates
    fuzzy_candidates = white_list.copy()
    print(f"模糊匹配候选列表加载完成，共 {len(fuzzy_candidates)} 项")
    
    # 加载替换规则
    replace_rules = load_replace_rules(replace_rules_path)
    print(f"替换规则加载完成，共 {len(replace_rules)} 条")
    
    # 初始化OCR
    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping = False,
        # device="gpu",
        use_textline_orientation=False,
        engine="transformers",
    )
    print("OCR引擎初始化完成")
    
    # 获取所有图片文件
    image_patterns = ["*.jpg", "*.png", "*.jpeg", "*.jxr"]
    image_files = []
    for pattern in image_patterns:
        image_files.extend(glob.glob(os.path.join(image_folder, pattern)))
    
    # image_files.sort()
    print(f"找到 {len(image_files)} 张图片")

    # 加载CSV提交时间
    csv_submission_times, rowcol_to_time = load_csv_submission_times(csv_path)
    print(f"CSV提交时间加载完成，{len(csv_submission_times)} 条文件名映射，{len(rowcol_to_time)} 条row/col映射")

    # 处理所有图片并收集结果
    all_results = []
    warning_results = []
    warning_count = 0
    file_count = 0
    for image_path in image_files:
        print(f"正在处理: {os.path.basename(image_path)}, 已处理 {file_count} 张图片")
        matched_items, item_discounts, warning, uid, remaining_refresh, refresh_hour = process_image(ocr, image_path, white_list, replace_rules)
        if warning:
            warning_count += 1

        img_datetime, time_source = get_image_datetime(image_path, csv_submission_times, rowcol_to_time)
        datetime_str = img_datetime.strftime('%Y-%m-%d %H:%M:%S') if img_datetime else ''

        if matched_items:
            for item, discount in zip(matched_items, item_discounts):
                result_dict = {
                    "filename": os.path.basename(image_path),
                    "item": item,
                    "discount": discount,
                    "datetime": datetime_str,
                    "time_source": time_source,
                    "uid": uid,
                    "remaining_refresh": remaining_refresh,
                    "refresh_hour": refresh_hour
                }
                if warning:
                    result_dict["warning"] = warning
                    warning_results.append(result_dict)
                else:
                    all_results.append(result_dict)
        else:
            result_dict = {
                "filename": os.path.basename(image_path),
                "item": "",
                "discount": "0",
                "datetime": datetime_str,
                "time_source": time_source,
                "uid": uid,
                "remaining_refresh": remaining_refresh,
                "refresh_hour": refresh_hour
            }
            if warning:
                result_dict["warning"] = warning
                warning_results.append(result_dict)
            else:
                all_results.append(result_dict)
        file_count += 1

    with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "item", "discount", "datetime", "time_source", "uid", "remaining_refresh", "refresh_hour"])
        writer.writeheader()
        writer.writerows(all_results)
    
    print(f"结果已保存到 {output_csv}")
    
    # 写入警告结果CSV
    if warning_results:
        with open(warning_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["filename", "item", "discount", "datetime", "time_source", "uid", "remaining_refresh", "refresh_hour", "warning"])
            writer.writeheader()
            writer.writerows(warning_results)
        
        print(f"警告结果已保存到 {warning_csv}")

    with open(warning_count_txt, 'w', encoding='utf-8-sig') as f:
        f.write(f"警告数量: {warning_count}")
        print(f"警告数量: {warning_count}")

if __name__ == "__main__":
    main()