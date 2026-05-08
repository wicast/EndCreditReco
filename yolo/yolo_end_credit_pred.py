from ultralytics import YOLO
import os

# 加载模型（以 YOLOv26 Nano 为例）
model = YOLO("runs/detect/end_credit_custom_model/weights/best.pt")

# 推理
input_file = "extra/IMG_20260214_164156.jpg"
results = model(input_file)

# 提取输入文件名（不含路径）
input_filename = os.path.basename(input_file)

# 确保输出目录存在
output_dir = "yolo_pred"
os.makedirs(output_dir, exist_ok=True)

# 查看结果，输出文件名跟随输入文件名变化
for r in results:
    # r.show()       # 显示标注图片
    # print(r.boxes) # 输出检测框信息
    output_path = os.path.join(output_dir, input_filename)
    r.save(output_path)
    print(f"预测结果已保存到: {output_path}")