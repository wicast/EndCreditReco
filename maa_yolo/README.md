# Items 物品检测模型

> 🌐 [English Version](README_EN.md)

本目录存放用于《明日方舟：终末地》（Arknights: Endfield）游戏内普通物品自动检测的 YOLO 目标检测模型。

## ⚠️ 模型状态说明

当前模型处于初步开发阶段，检测效果可能不够稳定。如果您在使用过程中遇到以下情况，欢迎通过 Issue 反馈：

- 误识别（将物品识别为错误的类别）
- 漏识别（未能检测到画面中的物品）
- 其他异常表现

您的反馈将帮助我们持续改进模型质量，感谢支持。

## 模型用途

这些模型能够对游戏截图进行目标检测，自动识别并定位画面中出现的各类普通物品，包括但不限于：

- 各类材料（源矿、紫晶矿、蓝铁矿、碳块等）
- 食物与料理（武陵炒饭、竹笋炒肉、清炖兽排参须汤等）
- 药剂与消耗品（柑实冲剂、荞愈胶囊、芽针喷剂等）
- 种子与农作物（柑实种子、砂叶种子、荞花种子等）
- 加工中间产物（晶体外壳粉末、致密源石粉末等）
- 其他游戏道具（信用、理智、折金票、通行证经验等）

完整类别列表共计 190+ 种，详见 [`classes.txt`](classes.txt)。

## 模型文件

本目录提供两种 YOLO 架构版本，每种架构均包含 Medium 和 Nano 两种规格：

| 文件 | 架构 | 规格 | 说明 |
|------|------|------|------|
| `yolo11/EF_items_11m.pt` | YOLOv11 | Medium | 精度较高，推理速度适中 |
| `yolo11/EF_items_11n.pt` | YOLOv11 | Nano | 轻量级，推理速度快，适合实时场景 |
| `yolo26/EF_items_26m.pt` | YOLOv26 | Medium | 新架构，精度较高，推理速度适中 |
| `yolo26/EF_items_26n.pt` | YOLOv26 | Nano | 新架构，轻量级，推理速度快 |

### 如何选择

- 追求检测精度 → 选择 Medium（`m`）规格
- 追求推理速度或部署在低算力设备上 → 选择 Nano（`n`）规格
- YOLOv26 为更新的架构，通常在同规格下表现优于 YOLOv11

## 效果演示

> 以下演示截图均为 Medium（`m`）模型的输出结果。Nano（`n`）模型效果有待测试。

![演示1](res/res%20(1).jpg)
![演示2](res/res%20(2).jpg)
![演示3](res/res%20(3).jpg)
![演示4](res/res%20(4).jpg)
![演示5](res/res%20(5).jpg)

## 快速使用

```bash
pip install ultralytics
```

```python
from ultralytics import YOLO

# 加载模型（以 YOLOv26 Nano 为例）
model = YOLO("items/yolo26/EF_items_26n.pt")

# 推理
results = model("screenshot.png")

# 查看结果
for r in results:
    r.show()       # 显示标注图片
    print(r.boxes) # 输出检测框信息
```

更多用法请参考 [Ultralytics 官方文档](https://docs.ultralytics.com/)。
