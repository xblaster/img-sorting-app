import os
import shutil
from datetime import datetime
import argparse
from tqdm import tqdm
from PIL import Image, UnidentifiedImageError
from moviepy.editor import VideoFileClip
import re
from datetime import datetime

def get_media_date(media_path):
    if media_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
        return get_image_date(media_path)
    elif media_path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')):
        return get_video_date(media_path)
    return None

def get_filename_date(media_path):
    filename = os.path.basename(media_path)
    # Simplified and ordered patterns
    date_patterns = [
        (r'(\d{4})(\d{2})(\d{2})', '%Y%m%d'),                # YYYYMMDD
        (r'(\d{2})(\d{2})(\d{4})', '%m%d%Y'),                # MMDDYYYY
        (r'(\d{4})[-/\.](\d{2})[-/\.](\d{2})', '%Y-%m-%d'),  # YYYY-MM-DD
        (r'(\d{2})[-/\.](\d{2})[-/\.](\d{4})', '%d-%m-%Y'),  # DD-MM-YYYY
        (r'(\d{2})[-/\.](\d{2})[-/\.](\d{2})', '%y-%m-%d'),  # YY-MM-DD
        (r'(\d{2})[-/\.](\d{2})[-/\.](\d{2})', '%d-%m-%y')   # DD-MM-YY
    ]
    for pattern, date_format in date_patterns:
        match = re.search(pattern, filename)
        if match:
            try:
                return datetime.strptime(''.join(match.groups()), date_format)
            except ValueError as e:
                print(f"Date parsing error in file {filename}: {e}")
                continue  # Continue trying other patterns if one fails
    print(f"No valid date found in filename {filename}")
    return None

def get_image_date(image_path):
    try:
        with Image.open(image_path) as img:
            exif_data = img._getexif()
            if exif_data:
                date_str = exif_data.get(36867)
                if date_str:
                    return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
    except UnidentifiedImageError:
        pass
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
    return None

def get_video_date(video_path):
    try:
        with VideoFileClip(video_path) as video:
            date_str = video.creation_date
            if date_str:
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        return get_filename_date(video_path)
    return None

def sort_media(source_dir, dest_dir, qualifier=None, dry_run=False, filter_pxl=False):
    media_paths = [os.path.join(dp, f) for dp, dn, filenames in os.walk(source_dir) for f in filenames if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv'))]
    
    if filter_pxl:
        media_paths = [path for path in media_paths if os.path.basename(path).startswith("PXL")]
    
    for media_path in tqdm(media_paths, desc="Sorting Media"):
        date = get_media_date(media_path) 
        if date:
            if qualifier:
                new_dir = os.path.join(dest_dir, f"{date.year}/{date.month:02}/{qualifier}")
            else:
                new_dir = os.path.join(dest_dir, f"{date.year}/{date.month:02}")
            if not dry_run:
                os.makedirs(new_dir, exist_ok=True)
                shutil.move(media_path, os.path.join(new_dir, os.path.basename(media_path)))
            print(f"Dry Run: Moving {media_path} to {os.path.join(new_dir, os.path.basename(media_path))}" if dry_run else f"Moving {media_path} to {os.path.join(new_dir, os.path.basename(media_path))}")
        else:
            print(f"No date found for {media_path}")

def main():
    parser = argparse.ArgumentParser(description="Sort media files by date into folders.")
    parser.add_argument("source_dir", help="Source directory containing media files to sort.")
    parser.add_argument("dest_dir", help="Destination directory to store sorted media files.")
    parser.add_argument("--qualifier", help="Optional qualifier for sub-folder categorization.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate the sorting process without moving any files.")
    parser.add_argument("--filter-pxl", action="store_true", help="Only process files starting with 'PXL'.")
    
    args = parser.parse_args()
    
    sort_media(args.source_dir, args.dest_dir, args.qualifier, args.dry_run, args.filter_pxl)

if __name__ == "__main__":
    main()