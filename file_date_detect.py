import os
import io
import re
import contextlib
import exifread
from datetime import datetime
from typing import Optional, Tuple


def get_exif_datetime(image_path: str) -> Optional[datetime]:
    """
    从图片EXIF数据中获取拍摄时间
    
    :param image_path: 图片文件路径
    :return: 拍摄时间datetime对象，如果无法获取则返回None
    """
    try:
        with open(image_path, 'rb') as f:
            try:
                old_stderr = io.StringIO()
                with contextlib.redirect_stderr(old_stderr):
                    tags = exifread.process_file(f, details=False)
            except Exception as e:
                return None
            
            datetime_tags = [
                'EXIF DateTimeOriginal',
                'EXIF DateTimeDigitized',
                'Image DateTime',
                'GPS GPSDate',
                'GPS GPSTimeStamp'
            ]
            
            for tag in datetime_tags:
                if tag in tags:
                    date_str = str(tags[tag])
                    date_str = date_str.strip()
                    if date_str:
                        formats = [
                            '%Y:%m:%d %H:%M:%S',
                            '%Y-%m-%d %H:%M:%S',
                            '%Y/%m/%d %H:%M:%S',
                            '%Y:%m:%d',
                            '%Y-%m-%d',
                            '%Y/%m/%d'
                        ]
                        for fmt in formats:
                            try:
                                return datetime.strptime(date_str, fmt)
                            except ValueError:
                                continue
        return None
    except (FileNotFoundError, PermissionError, OSError):
        return None


def get_file_creation_time(file_path: str) -> Optional[datetime]:
    """
    获取文件的创建时间
    
    :param file_path: 文件路径
    :return: 文件创建时间datetime对象，如果无法获取则返回None
    """
    try:
        if os.name == 'nt':
            # Windows系统
            ctime = os.path.getctime(file_path)
            return datetime.fromtimestamp(ctime)
        else:
            # Unix/Linux系统
            stat = os.stat(file_path)
            try:
                return datetime.fromtimestamp(stat.st_birthtime)
            except AttributeError:
                # 如果没有birthtime，返回修改时间
                return datetime.fromtimestamp(stat.st_mtime)
    except Exception:
        return None


def load_csv_submission_times(csv_path: str) -> dict:
    """
    从问卷CSV文件中加载提交时间，构建文件名到提交时间的映射

    :param csv_path: CSV文件路径
    :return: 字典，键为文件名，值为提交时间datetime对象
    """
    filename_to_time = {}
    if not os.path.exists(csv_path):
        return filename_to_time

    try:
        import csv as csv_module
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv_module.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 3:
                    submission_time_str = row[2].strip()
                    if submission_time_str:
                        try:
                            submission_time = datetime.strptime(submission_time_str, '%Y/%m/%d')
                            for col in range(4, min(len(row), 10)):
                                filename = row[col].strip()
                                if filename and filename not in filename_to_time:
                                    filename_to_time[filename] = submission_time
                        except ValueError:
                            continue
    except Exception:
        pass

    return filename_to_time


def get_image_datetime(image_path: str, csv_submission_times: dict = None) -> Tuple[Optional[datetime], str]:
    """
    获取图片的时间，优先使用拍摄时间，其次使用文件名解析时间，再次使用CSV提交时间，最后使用文件创建时间

    :param image_path: 图片文件路径
    :param csv_submission_times: 可选的字典，文件名到提交时间的映射
    :return: (datetime对象, 时间来源描述)
    """
    if not os.path.exists(image_path):
        return None, '文件不存在'

    filename = os.path.basename(image_path)

    # 优先获取EXIF拍摄时间
    exif_time = get_exif_datetime(image_path)
    if exif_time:
        return exif_time, 'EXIF拍摄时间'

    # 从文件名解析时间作为备选
    filename_time = parse_datetime_from_filename(filename)
    if filename_time:
        return filename_time, '文件名解析时间'

    # 使用CSV提交时间作为备选
    if csv_submission_times and filename in csv_submission_times:
        csv_time = csv_submission_times[filename]
        if csv_time:
            return csv_time, 'CSV提交时间'

    # 获取文件创建时间作为最后备选
    file_time = get_file_creation_time(image_path)
    if file_time:
        return file_time, '文件创建时间'

    return None, '无法获取时间'


def format_datetime(dt: datetime, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    格式化datetime对象为字符串
    
    :param dt: datetime对象
    :param fmt: 格式化字符串，默认为'%Y-%m-%d %H:%M:%S'
    :return: 格式化后的时间字符串
    """
    return dt.strftime(fmt)


def parse_datetime_from_filename(filename: str) -> Optional[datetime]:
    """
    从文件名中解析日期时间信息
    
    支持的文件名格式：
    - Screenshot_2026-02-14-16-09-12-08_xxx.jpg
    - Screenshot_20260214_163855_com.hypergryph.endfield.jpg
    - IMG_20260214_164141.jpg
    - 屏幕截图_20260214_170343.png
    - Endfield 2026_2_14 16_58_49.png
    - QQ20260214-233429.png
    - QQ截图20260215111702.png
    - 屏幕截图 2026-02-14 214410.png
    - Snipaste_2026-02-14_22-45-00.jpg
    - Endfield Screenshot 2026.02.15 - 09.52.34.04.png
    - Image_1771116366818_426.png (Unix时间戳)
    
    :param filename: 文件名
    :return: datetime对象，如果无法解析则返回None
    """
    patterns = [
        # Screenshot_2026-02-14-16-09-12-08_xxx.jpg
        (r'Screenshot_(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})', '%Y-%m-%d-%H-%M-%S'),
        # Screenshot_20260214_163855_com.hypergryph.endfield.jpg
        (r'Screenshot_(\d{8})_(\d{6})', '%Y%m%d_%H%M%S'),
        # IMG_20260214_164141.jpg
        (r'IMG_(\d{8})_(\d{6})', '%Y%m%d_%H%M%S'),
        # IMG20260214192616.jpg
        (r'IMG(\d{14})', '%Y%m%d%H%M%S'),
        # 屏幕截图_20260214_170343.png
        (r'屏幕截图_(\d{8})_(\d{6})', '%Y%m%d_%H%M%S'),
        # 屏幕截图 2026-02-14 214410.png
        (r'屏幕截图 (\d{4})-(\d{2})-(\d{2}) (\d{6})', '%Y-%m-%d %H%M%S'),
        # Endfield 2026_2_14 16_58_49.png
        (r'Endfield (\d{4})_(\d{1,2})_(\d{1,2}) (\d{1,2})_(\d{2})_(\d{2})', '%Y_%m_%d %H_%M_%S'),
        # Endfield Screenshot 2026.02.15 - 09.52.34.04.png
        (r'Endfield Screenshot (\d{4})\.(\d{2})\.(\d{2}) - (\d{2})\.(\d{2})\.(\d{2})', '%Y.%m.%d - %H.%M.%S'),
        # QQ20260214-233429.png
        (r'QQ(\d{8})-(\d{6})', '%Y%m%d-%H%M%S'),
        # QQ截图20260215111702.png
        (r'QQ截图(\d{14})', '%Y%m%d%H%M%S'),
        # QQ_1771079329465.png (Unix时间戳)
        (r'QQ_(\d{13})', '%Y%m%d%H%M%S'),
        # Snipaste_2026-02-14_22-45-00.jpg
        (r'Snipaste_(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})', '%Y-%m-%d_%H-%M-%S'),
        # ScreenShot_2026-02-15_102727_599.png
        (r'ScreenShot_(\d{4})-(\d{2})-(\d{2})_(\d{6})', '%Y-%m-%d_%H%M%S'),
        # 联想截图_20260215111356.png
        (r'联想截图_(\d{14})', '%Y%m%d%H%M%S'),
        # Screenshot 2026-02-15 111029.png
        (r'Screenshot (\d{4})-(\d{2})-(\d{2}) (\d{6})', '%Y-%m-%d %H%M%S'),
        # 20260214未刷新.jpg
        (r'(\d{8})未刷新', '%Y%m%d'),
        # 260216_first80.png
        (r'(\d{2})(\d{2})(\d{2})_first', '%y%m%d'),
        # Image_1771116366818_426.png (Unix时间戳，毫秒)
        (r'Image_(\d{13})_', '%Y%m%d%H%M%S'),
        # mmexport1771109552907.png (Unix时间戳，毫秒)
        (r'mmexport(\d{13})', '%Y%m%d%H%M%S'),
    ]
    
    for pattern, fmt in patterns:
        match = re.search(pattern, filename)
        if match:
            try:
                date_str = match.group(0)
                # 提取匹配的部分并重新组合成格式化字符串
                parts = match.groups()
                if len(parts) == 6:  # YYYY, MM, DD, HH, MM, SS
                    date_str = f"{parts[0]}-{parts[1]}-{parts[2]} {parts[3]}:{parts[4]}:{parts[5]}"
                    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                elif len(parts) == 5:  # YYYY, M, D, H, M, S (部分可能是1位)
                    date_str = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d} {int(parts[3]):02d}:{int(parts[4]):02d}:{int(parts[5]):02d}"
                    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                elif len(parts) == 4:  # YYYY, MM, DD, HHMMSS
                    date_str = f"{parts[0]}-{parts[1]}-{parts[2]} {parts[3]}"
                    return datetime.strptime(date_str, '%Y-%m-%d %H%M%S')
                elif len(parts) == 3:  # YYYY, MM, DD 或 YY, MM, DD
                    if len(parts[0]) == 4:
                        date_str = f"{parts[0]}-{parts[1]}-{parts[2]}"
                        return datetime.strptime(date_str, '%Y-%m-%d')
                    else:  # YY格式
                        date_str = f"20{parts[0]}-{parts[1]}-{parts[2]}"
                        return datetime.strptime(date_str, '%Y-%m-%d')
                elif len(parts) == 2:  # YYYYMMDD, HHMMSS
                    date_str = f"{parts[0]}{parts[1]}"
                    return datetime.strptime(date_str, '%Y%m%d%H%M%S')
                elif len(parts) == 1:
                    date_str = parts[0]
                    if len(date_str) == 14:  # YYYYMMDDHHMMSS
                        return datetime.strptime(date_str, '%Y%m%d%H%M%S')
                    elif len(date_str) == 8:  # YYYYMMDD
                        return datetime.strptime(date_str, '%Y%m%d')
                    elif len(date_str) == 13:  # Unix时间戳（毫秒）
                        return datetime.fromtimestamp(int(date_str) / 1000)
            except (ValueError, IndexError):
                continue
    
    return None


def get_image_files(folder_path: str) -> list:
    """
    获取文件夹中所有图片文件的路径
    
    :param folder_path: 文件夹路径
    :return: 图片文件路径列表
    """
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.raw', '.heic')
    image_files = []
    
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) and filename.lower().endswith(image_extensions):
            image_files.append(file_path)
    
    return sorted(image_files)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='获取图片的创建时间或拍摄时间')
    parser.add_argument('-path', help='图片文件路径或图片文件夹路径', default=r"extra")
    parser.add_argument('-f', '--format', default='%Y-%m-%d %H:%M:%S', 
                        help='时间输出格式，默认为"%%Y-%%m-%%d %%H:%%M:%%S"')
    parser.add_argument('-csv', '--csv', 
                        help='问卷CSV文件路径，用于从提交时间获取备用时间',
                        default=r"d:\Projects\Python\EndCreditReco\问卷_问卷.csv")
    
    args = parser.parse_args()
    
    target_path = args.path
    
    if not os.path.exists(target_path):
        print(f'错误: 路径不存在 - {target_path}')
        return
    
    csv_submission_times = load_csv_submission_times(args.csv) if args.csv else {}
    
    if os.path.isfile(target_path):
        dt, source = get_image_datetime(target_path, csv_submission_times)
        if dt:
            formatted_time = format_datetime(dt, args.format)
            print(f'{os.path.basename(target_path)}')
            print(f'  时间: {formatted_time}')
            print(f'  来源: {source}')
        else:
            print(f'{os.path.basename(target_path)}')
            print(f'  无法获取时间: {source}')
    elif os.path.isdir(target_path):
        import csv as csv_module
        
        image_files = get_image_files(target_path)
        
        if not image_files:
            print(f'文件夹中没有找到图片文件 - {target_path}')
            return
        
        print(f'正在处理文件夹: {target_path}')
        print(f'共找到 {len(image_files)} 个图片文件')
        
        csv_path = os.path.join(target_path, 'image_datetime.csv')
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv_module.writer(csvfile)
            writer.writerow(['文件名', '时间', '时间来源'])
            
            for image_file in image_files:
                dt, source = get_image_datetime(image_file, csv_submission_times)
                if dt:
                    formatted_time = format_datetime(dt, args.format)
                    writer.writerow([os.path.basename(image_file), formatted_time, source])
                else:
                    writer.writerow([os.path.basename(image_file), '', '无法获取时间'])
        
        print(f'结果已保存到: {csv_path}')


if __name__ == '__main__':
    main()
