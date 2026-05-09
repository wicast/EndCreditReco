import os
import io
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


def get_image_datetime(image_path: str) -> Tuple[Optional[datetime], str]:
    """
    获取图片的时间，优先使用拍摄时间，其次使用文件创建时间
    
    :param image_path: 图片文件路径
    :return: (datetime对象, 时间来源描述)
    """
    if not os.path.exists(image_path):
        return None, '文件不存在'
    
    # 优先获取EXIF拍摄时间
    exif_time = get_exif_datetime(image_path)
    if exif_time:
        return exif_time, 'EXIF拍摄时间'
    
    # 获取文件创建时间作为备选
    # file_time = get_file_creation_time(image_path)
    # if file_time:
    #     return file_time, '文件创建时间'
    
    return None, '无法获取时间'


def format_datetime(dt: datetime, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    格式化datetime对象为字符串
    
    :param dt: datetime对象
    :param fmt: 格式化字符串，默认为'%Y-%m-%d %H:%M:%S'
    :return: 格式化后的时间字符串
    """
    return dt.strftime(fmt)


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
    parser.add_argument('-path', help='图片文件路径或图片文件夹路径',default=r"extra")
    parser.add_argument('-f', '--format', default='%Y-%m-%d %H:%M:%S', 
                        help='时间输出格式，默认为"%%Y-%%m-%%d %%H:%%M:%%S"')
    
    args = parser.parse_args()
    
    target_path = args.path
    
    if not os.path.exists(target_path):
        print(f'错误: 路径不存在 - {target_path}')
        return
    
    # 判断是文件还是文件夹
    if os.path.isfile(target_path):
        # 处理单个文件
        dt, source = get_image_datetime(target_path)
        if dt:
            formatted_time = format_datetime(dt, args.format)
            print(f'{os.path.basename(target_path)}')
            print(f'  时间: {formatted_time}')
            print(f'  来源: {source}')
        else:
            print(f'{os.path.basename(target_path)}')
            print(f'  无法获取时间: {source}')
    elif os.path.isdir(target_path):
        import csv
        
        image_files = get_image_files(target_path)
        
        if not image_files:
            print(f'文件夹中没有找到图片文件 - {target_path}')
            return
        
        print(f'正在处理文件夹: {target_path}')
        print(f'共找到 {len(image_files)} 个图片文件')
        
        csv_path = os.path.join(target_path, 'image_datetime.csv')
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['文件名', '时间', '时间来源'])
            
            for image_file in image_files:
                dt, source = get_image_datetime(image_file)
                if dt:
                    formatted_time = format_datetime(dt, args.format)
                    writer.writerow([os.path.basename(image_file), formatted_time, source])
                else:
                    writer.writerow([os.path.basename(image_file), '', '无法获取时间'])
        
        print(f'结果已保存到: {csv_path}')


if __name__ == '__main__':
    main()
