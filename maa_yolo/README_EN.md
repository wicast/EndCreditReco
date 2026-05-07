# Items — Item Detection Models

> 🌐 [中文版本](README.md)

This directory contains YOLO object detection models for automatic detection of common items in the game *Arknights: Endfield*.

## ⚠️ Model Status

This model is currently in an early development stage, and detection results may not be fully stable. If you encounter any of the following issues, please feel free to report them via Issues:

- Misidentification (item recognized as the wrong class)
- Missed detection (items in the screenshot not detected)
- Other unexpected behavior

Your feedback will help us continuously improve model quality. Thank you for your support.

## Purpose

These models perform object detection on game screenshots, automatically identifying and locating various common items on screen, including but not limited to:

- Materials (Originium Ore, Amethyst Ore, Blue Iron Ore, Carbon Block, etc.)
- Food & Dishes (Wuling Fried Rice, Bamboo Shoot Stir-fry, Stewed Beast Steak with Ginseng Soup, etc.)
- Potions & Consumables (Citrus Brew, Buckwheat Capsule, Sprout Needle Spray, etc.)
- Seeds & Crops (Citrus Seed, Sand Leaf Seed, Buckwheat Seed, etc.)
- Processed Intermediates (Crystal Shell Powder, Dense Originium Powder, etc.)
- Other Game Items (Credits, Sanity, Gold Ticket, Pass EXP, etc.)

The full class list contains 190+ categories. See [`classes.txt`](classes.txt) for details.

## Model Files

Two YOLO architecture versions are provided, each available in Medium and Nano variants:

| File | Architecture | Variant | Description |
|------|-------------|---------|-------------|
| `yolo11/EF_items_11m.pt` | YOLOv11 | Medium | Higher accuracy, moderate inference speed |
| `yolo11/EF_items_11n.pt` | YOLOv11 | Nano | Lightweight, fast inference, suitable for real-time scenarios |
| `yolo26/EF_items_26m.pt` | YOLOv26 | Medium | Newer architecture, higher accuracy, moderate inference speed |
| `yolo26/EF_items_26n.pt` | YOLOv26 | Nano | Newer architecture, lightweight, fast inference |

### How to Choose

- For best detection accuracy → choose Medium (`m`) variant
- For faster inference or deployment on low-compute devices → choose Nano (`n`) variant
- YOLOv26 is the newer architecture and generally outperforms YOLOv11 at the same variant level

## Demo

> The demo screenshots below are output from the Medium (`m`) models. Nano (`n`) model results are yet to be tested.

![Demo 1](res/res%20(1).jpg)
![Demo 2](res/res%20(2).jpg)
![Demo 3](res/res%20(3).jpg)
![Demo 4](res/res%20(4).jpg)
![Demo 5](res/res%20(5).jpg)

## Quick Start

```bash
pip install ultralytics
```

```python
from ultralytics import YOLO

# Load a model (YOLOv26 Nano as an example)
model = YOLO("items/yolo26/EF_items_26n.pt")

# Run inference
results = model("screenshot.png")

# View results
for r in results:
    r.show()       # Display the annotated image
    print(r.boxes) # Print detection box info
```

For more usage details, refer to the [official Ultralytics documentation](https://docs.ultralytics.com/).
