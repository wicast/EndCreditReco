from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_doc_orientation_classify=False, # 通过 use_doc_orientation_classify 参数指定不使用文档方向分类模型
    # device="gpu",
    use_doc_unwarping=False, # 通过 use_doc_unwarping 参数指定不使用文本图像矫正模型
    use_textline_orientation=False, # 通过 use_textline_orientation 参数指定不使用文本行方向分类模型
    engine="transformers",
)
# ocr = PaddleOCR(lang="en", engine="transformers") # 通过 lang 参数来使用英文模型
# ocr = PaddleOCR(ocr_version="PP-OCRv4") # 通过 ocr_version 参数来使用 PP-OCR 其他版本
# ocr = PaddleOCR(device="gpu", engine="transformers") # 通过 device 参数使得在模型推理时使用 GPU
# ocr = PaddleOCR(
#     text_detection_model_name="PP-OCRv5_server_det",
#     text_recognition_model_name="PP-OCRv5_server_rec",
#     use_doc_orientation_classify=False,
#     use_doc_unwarping=False,
#     use_textline_orientation=False,
#     engine="transformers",
# ) # 更换 PP-OCRv5_server 模型
result = ocr.predict("./extra/a525658c-1b39-4188-a457-3e294914c6e1.png")
for res in result:
    res.print()
    res.save_to_img("output")
    res.save_to_json("output")