import cv2
import numpy as np
import os

def resize_display(img, max_width=800, max_height=600, window_name="Result"):
    h, w = img.shape[:2]
    scale = min(max_width / w, max_height / h)
    if scale < 1:
        new_w = int(w * scale)
        new_h = int(h * scale)
        img_resized = cv2.resize(img, (new_w, new_h))
    else:
        img_resized = img.copy()
    cv2.imshow(window_name, img_resized)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def preprocess_for_glow(gray, blur_ksize=7, erode_iter=1, canny_low=25, canny_high=80):
    blurred = cv2.GaussianBlur(gray, (blur_ksize, blur_ksize), 0)
    kernel = np.ones((3,3), np.uint8)
    eroded = cv2.erode(blurred, kernel, iterations=erode_iter)
    edges = cv2.Canny(eroded, canny_low, canny_high)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    return closed

def remove_overlapping_rects(quads, iou_threshold=0.5):
    """Remove overlapping rectangles, keep the one with larger area."""
    if len(quads) <= 1:
        return quads
    quads_sorted = sorted(quads, key=lambda x: x['area_ratio'], reverse=True)
    keep = []
    for q in quads_sorted:
        keep_flag = True
        box1 = q['box']
        x1 = min(box1[:,0]); y1 = min(box1[:,1]); x2 = max(box1[:,0]); y2 = max(box1[:,1])
        area1 = (x2-x1)*(y2-y1)
        for kept in keep:
            box2 = kept['box']
            x1k = min(box2[:,0]); y1k = min(box2[:,1]); x2k = max(box2[:,0]); y2k = max(box2[:,1])
            area2 = (x2k-x1k)*(y2k-y1k)
            ix1 = max(x1, x1k); iy1 = max(y1, y1k); ix2 = min(x2, x2k); iy2 = min(y2, y2k)
            if ix2 > ix1 and iy2 > iy1:
                inter = (ix2-ix1)*(iy2-iy1)
                iou = inter / min(area1, area2)
                if iou > iou_threshold:
                    keep_flag = False
                    break
        if keep_flag:
            keep.append(q)
    return keep

def detect_quads(image_path,
                 min_area_ratio=0.01,
                 max_area_ratio=0.06,
                 aspect_ratio_range=(0.9, 1.6),
                 angle_range=(0, 20),
                 solidity_threshold=0.5,
                 glow_erode_iter=1,
                 blur_ksize=7,
                 canny_low=25,
                 canny_high=80,
                 debug=True):
    """
    Detect quadrilateral borders using rotated rectangle directly.
    Applies overlap removal (keeping larger rectangle).
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Cannot read image")

    img = cv2.GaussianBlur(img, (5, 5), 0)
    
    img_area = img.shape[0] * img.shape[1]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_eq = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(gray)

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

        # For debug: compute approx vertex count
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        vertex_count = len(approx)

        quads.append({
            "box": box,
            "center": center,
            "area_ratio": area_ratio,
            "aspect": aspect,
            "angle": angle_norm,
            "size": (w, h),
            "solidity": solidity,
            "vertex_count": vertex_count
        })

    # Apply overlap removal
    quads = remove_overlapping_rects(quads, iou_threshold=0.5)

    # Draw results with thickness 10
    result_img = img.copy()
    for q in quads:
        cv2.drawContours(result_img, [q["box"]], 0, (0, 255, 0), 10)
        center_pt = tuple(map(int, q["center"]))
        cv2.circle(result_img, center_pt, 3, (0, 0, 255), -1)

    if debug:
        print(f"Detected {len(quads)} quadrilaterals (after overlap removal)")
        for idx, q in enumerate(quads, start=1):
            print(f"  #{idx}: area_ratio={q['area_ratio']:.6f}, aspect={q['aspect']:.3f}, angle={q['angle']:.2f}, solidity={q['solidity']:.3f}, vertices={q['vertex_count']}")

    return quads, result_img


if __name__ == "__main__":
    test_dir = "test_img"
    for file in os.listdir(test_dir):
        file_path = os.path.join(test_dir, file)
        if not os.path.isfile(file_path):
            continue
        print(f"\n=== Processing: {file} ===")
        try:            
            # 物品本体
            # quads, output = detect_quads(file_path,
            #                                 min_area_ratio=0.005,
            #                                 max_area_ratio=0.06,
            #                                 aspect_ratio_range=(1.0, 1.6),
            #                                 angle_range=(0, 20),
            #                                 solidity_threshold=0.0, 
            #                                 debug=True)
            
            # 立即刷新
            quads, output = detect_quads(file_path,
                                            min_area_ratio=0.001,
                                            max_area_ratio=0.006,
                                            aspect_ratio_range=(3, 10),
                                            angle_range=(0, 5),
                                            solidity_threshold=0.0, 
                                            debug=True)
            
            resize_display(output, max_width=1000, max_height=800, window_name=f"Quads - {file}")
        except Exception as e:
            print(f"  Error: {e}")