# from ultralytics.utils.checks import check_font
# print(check_font("Arial.ttf"))  # 会返回字体完整路径

# from ultralytics import YOLO

# # 加载模型（以 YOLOv26 Nano 为例）
# model = YOLO("items/yolo26/EF_items_26n.pt")

# # 推理
# results = model("屏幕截图 2026-05-06 185429.png")

# # 查看结果
# for r in results:
#     r.show()       # 显示标注图片
#     print(r.boxes) # 输出检测框信息


from ultralytics import YOLO
import os

if __name__ == "__main__":
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 项目根目录（yolo目录的父目录）
    project_root = os.path.dirname(script_dir)
    # yaml文件的绝对路径
    data_yaml_path = os.path.join(project_root, "end_credit_yolo_dataset/end_credit_yolo_dataset.yaml")
    
    # Load a pretrained YOLO26n model
    model = YOLO("maa_yolo/yolo26/EF_items_26n.pt")

    # Train the model on custom dataset
    results = model.train(data=data_yaml_path, epochs=100, imgsz=640, name="end_credit_custom_model")