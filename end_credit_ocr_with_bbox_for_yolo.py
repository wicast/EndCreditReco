import os
import glob
import re
import shutil
import cv2
import numpy as np
import argparse
from paddleocr import PaddleOCR

# 配置路径
image_folder = r"信用商店"
white_list_path = r"target.txt"
replace_rules_path = r"replace.txt"

# YOLO训练集输出配置
yolo_output_dir = "end_credit_yolo_dataset"
yolo_images_train_dir = os.path.join(yolo_output_dir, "images", "train")
yolo_images_val_dir = os.path.join(yolo_output_dir, "images", "val")
yolo_labels_train_dir = os.path.join(yolo_output_dir, "labels", "train")
yolo_labels_val_dir = os.path.join(yolo_output_dir, "labels", "val")
yolo_data_yaml = os.path.join(yolo_output_dir, f"{yolo_output_dir}.yaml")

# 训练集/验证集划分比例
train_val_split = 0.8  # 80%训练集，20%验证集


# 用正则表达式尝试模糊匹配ocr识别错误
fuzzy_regex = [
    (r'[衫韧初级].*[知认人载体]', '初级认知载体'),
    (r'中.*[记录]', '中级作战记录'),
    (r'[衫韧初级].*[记录]', '初级作战记录'),
    (r'[重型].*[具]', '重型强固模具'),
    (r'[武器检查试赋].*[装置]', '武器检查装置'),
    (r'[武器检查试赋].*[单元]', '武器检查单元'),
    (r'[圆盘].*[目组]', '协议圆盘组'),
]


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


def preprocess_for_glow(gray, blur_ksize=7, erode_iter=1, canny_low=25, canny_high=80):
    """预处理图像用于边框检测"""
    blurred = cv2.GaussianBlur(gray, (blur_ksize, blur_ksize), 0)
    kernel = np.ones((3, 3), np.uint8)
    eroded = cv2.erode(blurred, kernel, iterations=erode_iter)
    edges = cv2.Canny(eroded, canny_low, canny_high)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    return closed


def remove_overlapping_rects(quads, iou_threshold=0.5):
    """移除重叠矩形，保留面积较大的"""
    if len(quads) <= 1:
        return quads
    quads_sorted = sorted(quads, key=lambda x: x['area_ratio'], reverse=True)
    keep = []
    for q in quads_sorted:
        keep_flag = True
        box1 = q['box']
        x1 = min(box1[:, 0])
        y1 = min(box1[:, 1])
        x2 = max(box1[:, 0])
        y2 = max(box1[:, 1])
        area1 = (x2 - x1) * (y2 - y1)
        for kept in keep:
            box2 = kept['box']
            x1k = min(box2[:, 0])
            y1k = min(box2[:, 1])
            x2k = max(box2[:, 0])
            y2k = max(box2[:, 1])
            area2 = (x2k - x1k) * (y2k - y1k)
            ix1 = max(x1, x1k)
            iy1 = max(y1, y1k)
            ix2 = min(x2, x2k)
            iy2 = min(y2, y2k)
            if ix2 > ix1 and iy2 > iy1:
                inter = (ix2 - ix1) * (iy2 - iy1)
                iou = inter / min(area1, area2)
                if iou > iou_threshold:
                    keep_flag = False
                    break
        if keep_flag:
            keep.append(q)
    return keep


def cv2_imread(image_path):
    """读取图像，支持中文路径"""
    img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    return img


def detect_object_boxes(image_path,
                        min_area_ratio=0.01,
                        max_area_ratio=0.06,
                        aspect_ratio_range=(0.9, 1.6),
                        angle_range=(0, 20),
                        solidity_threshold=0.5,
                        glow_erode_iter=1,
                        blur_ksize=7,
                        canny_low=25,
                        canny_high=80,
                        debug=False):
    """
    检测图片中的物体边框
    返回检测到的边框列表和处理后的图像
    """
    img = cv2_imread(image_path)
    if img is None:
        raise ValueError("Cannot read image")

    img = cv2.GaussianBlur(img, (5, 5), 0)
    img_area = img.shape[0] * img.shape[1]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_eq = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)

    binary = preprocess_for_glow(gray_eq, blur_ksize, glow_erode_iter, canny_low, canny_high)
    contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    quads = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        area_ratio = area / img_area
        if area_ratio < min_area_ratio or area_ratio > max_area_ratio:
            continue

        rect = cv2.minAreaRect(cnt)
        w, h = rect[1]
        if w < h:
            w, h = h, w
        aspect = w / h if h > 0 else 0
        if aspect < aspect_ratio_range[0] or aspect > aspect_ratio_range[1]:
            continue

        angle_raw = rect[2]
        angle_norm = abs(angle_raw)
        if angle_norm > 45:
            angle_norm = 90 - angle_norm
        if angle_norm < angle_range[0] or angle_norm > angle_range[1]:
            continue

        solidity = area / (w * h) if w * h > 0 else 0
        if solidity < solidity_threshold:
            continue

        box = cv2.boxPoints(rect)
        box = box.astype(np.int32)
        center = rect[0]

        quads.append({
            "box": box,
            "center": center,
            "area_ratio": area_ratio,
            "aspect": aspect,
            "angle": angle_norm,
            "size": (w, h),
            "solidity": solidity
        })

    quads = remove_overlapping_rects(quads, iou_threshold=0.5)

    # 按y坐标排序（从上到下），然后按x坐标排序（从左到右）
    quads.sort(key=lambda x: (x['center'][1], x['center'][0]))

    if debug:
        print(f"Detected {len(quads)} object boxes")

    return quads


def crop_image_by_box(img, box):
    """根据边框裁剪图像区域"""
    x1 = max(0, int(min(box[:, 0])))
    y1 = max(0, int(min(box[:, 1])))
    x2 = min(img.shape[1], int(max(box[:, 0])))
    y2 = min(img.shape[0], int(max(box[:, 1])))
    
    # 稍微扩大边界，确保包含完整内容
    padding = 5
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(img.shape[1], x2 + padding)
    y2 = min(img.shape[0], y2 + padding)
    
    return img[y1:y2, x1:x2]


def get_item_class_id(item_name, white_list):
    """获取物品的类别ID（基于白名单中的索引）"""
    if item_name in white_list:
        return white_list.index(item_name)
    return -1


def write_yolo_label(label_path, item_boxes, img_width, img_height, white_list):
    """
    写入YOLO格式的标签文件
    格式：class_id x_center y_center width height（归一化坐标）
    """
    with open(label_path, 'w', encoding='utf-8') as f:
        for box_info in item_boxes:
            box = box_info['box']
            item_name = box_info.get('item', '')
            
            class_id = get_item_class_id(item_name, white_list)
            if class_id == -1:
                continue
            
            # 计算边界框坐标
            x1 = min(box[:, 0])
            y1 = min(box[:, 1])
            x2 = max(box[:, 0])
            y2 = max(box[:, 1])
            
            # 归一化
            x_center = (x1 + x2) / 2 / img_width
            y_center = (y1 + y2) / 2 / img_height
            width = (x2 - x1) / img_width
            height = (y2 - y1) / img_height
            
            # 写入标签
            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")


def write_yolo_data_yaml(yaml_path, white_list):
    """
    生成YOLO训练配置文件data.yaml
    """
    yaml_content = f"""path: {yolo_output_dir}
train: images/train
val: images/val
test: 

nc: {len(white_list)}
names: {[item for item in white_list]}
"""
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)


def process_image_with_bbox(ocr, image_path, white_list, replace_rules=None, debug=False):
    """处理单张图片，先检测边框再对边框内进行OCR"""
    try:
        # 检测物品边框
        item_boxes = detect_object_boxes(image_path,
                                         min_area_ratio=0.005,
                                         max_area_ratio=0.06,
                                         aspect_ratio_range=(1.0, 1.6),
                                         angle_range=(0, 20),
                                         solidity_threshold=0.0,
                                         debug=debug)
        
        # 读取原始图像
        img = cv2_imread(image_path)
        if img is None:
            raise ValueError("Cannot read image")
        
        img_height, img_width = img.shape[:2]
        
        # 对每个物品边框进行OCR，同时提取物品名称和折扣信息
        matched_items = []
        item_discounts = []
        # 用于YOLO标签的边框信息（包含物品名称）
        labeled_boxes = []
        
        for item_box in item_boxes:
            # 裁剪边框区域
            cropped_img = crop_image_by_box(img, item_box['box'])
            
            # 对裁剪区域进行OCR
            result = ocr.predict(cropped_img)
            
            rec_texts = []
            for res in result:
                rec_texts.extend(res['rec_texts'])
            
            # 在识别结果中查找白名单匹配项
            matched_item = None
            for text in rec_texts:
                # 先尝试精确匹配
                if text in white_list:
                    matched_item = text
                    break
            
            # 如果没有精确匹配，尝试模糊匹配
            if matched_item is None:
                for text in rec_texts:
                    for reg, correct_name in fuzzy_regex:
                        if re.search(reg, text):
                            matched_item = correct_name
                            break
                    if matched_item:
                        break
            
            # 如果应用替换规则
            if matched_item and replace_rules:
                matched_item = apply_replace_rules(matched_item, replace_rules)
            
            # 在识别结果中查找折扣信息（包含%的文本）
            discount_text = "0"
            for text in rec_texts:
                if '%' in text:
                    discount_text = text
                    break
            
            if matched_item:
                matched_items.append(matched_item)
                item_discounts.append(discount_text)
                # 添加到带标签的边框列表
                labeled_boxes.append({
                    'box': item_box['box'],
                    'item': matched_item,
                    'discount': discount_text
                })
        
        # 检查matched_items数量是否为10
        warning = ""
        if len(matched_items) != 10:
            warning = f"警告：matched_items数量为 {len(matched_items)}，预期为10"
            print(warning)
            
            # 保存问题图片
            output_dir = "问题图片"
            os.makedirs(output_dir, exist_ok=True)
            dest_image_path = os.path.join(output_dir, os.path.basename(image_path))
            shutil.copy(image_path, dest_image_path)
        
        return matched_items, item_discounts, warning, labeled_boxes, img_width, img_height
    except Exception as e:
        print(f"处理图片 {image_path} 时出错: {e}")
        return [], [], str(e), [], 0, 0


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="OCR识别信用商店物品 - 输出YOLO训练集")
    args = parser.parse_args()
    
    # 创建YOLO输出目录结构
    os.makedirs(yolo_images_train_dir, exist_ok=True)
    os.makedirs(yolo_images_val_dir, exist_ok=True)
    os.makedirs(yolo_labels_train_dir, exist_ok=True)
    os.makedirs(yolo_labels_val_dir, exist_ok=True)
    print(f"YOLO训练集输出目录: {yolo_output_dir}")
    
    # 加载白名单
    white_list = load_white_list(white_list_path)
    print(f"白名单加载完成，共 {len(white_list)} 项")
    
    # 生成YOLO配置文件data.yaml
    write_yolo_data_yaml(yolo_data_yaml, white_list)
    print(f"YOLO配置文件已生成: {yolo_data_yaml}")
    
    # 加载替换规则
    replace_rules = load_replace_rules(replace_rules_path)
    print(f"替换规则加载完成，共 {len(replace_rules)} 条")
    
    # 初始化OCR
    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
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
    
    print(f"找到 {len(image_files)} 张图片")
    
    # 打乱图片顺序（用于随机划分训练集/验证集）
    import random
    random.shuffle(image_files)
    
    # 计算训练集/验证集分割点
    split_idx = int(len(image_files) * train_val_split)
    
    # 处理所有图片
    warning_count = 0
    train_count = 0
    val_count = 0
    file_count = 0
    
    for idx, image_path in enumerate(image_files):
        print(f"正在处理: {os.path.basename(image_path)}, 已处理 {file_count} 张图片")
        matched_items, _, warning, labeled_boxes, img_width, img_height = process_image_with_bbox(ocr, image_path, white_list, replace_rules)
        
        if warning:
            warning_count += 1
        
        # 输出YOLO训练集
        if labeled_boxes:
            # 判断是训练集还是验证集
            is_train = idx < split_idx
            
            if is_train:
                img_dst_dir = yolo_images_train_dir
                label_dst_dir = yolo_labels_train_dir
                set_name = "train"
                train_count += 1
            else:
                img_dst_dir = yolo_images_val_dir
                label_dst_dir = yolo_labels_val_dir
                set_name = "val"
                val_count += 1
            
            # 复制图片到对应目录
            img_basename = os.path.basename(image_path)
            dst_img_path = os.path.join(img_dst_dir, img_basename)
            shutil.copy(image_path, dst_img_path)
            
            # 生成标签文件
            label_basename = os.path.splitext(img_basename)[0] + ".txt"
            label_path = os.path.join(label_dst_dir, label_basename)
            write_yolo_label(label_path, labeled_boxes, img_width, img_height, white_list)
            print(f"  -> [{set_name}] YOLO标签已保存: {label_path} (物品数量: {len(labeled_boxes)})")
        else:
            print(f"  -> 未检测到物品，跳过")
        
        file_count += 1
    
    print(f"\n处理完成！")
    print(f"总图片数: {len(image_files)}")
    print(f"训练集数量: {train_count}")
    print(f"验证集数量: {val_count}")
    print(f"有警告的图片数: {warning_count}")


if __name__ == "__main__":
    main()
