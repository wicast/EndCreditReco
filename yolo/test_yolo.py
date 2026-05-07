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

if __name__ == "__main__":
    # Load a pretrained YOLO26n model
    model = YOLO("yolo26n.pt")

    # Train the model on COCO8
    results = model.train(data="coco8.yaml", epochs=100, imgsz=640, name="my_custom_model")