import os
import shutil
from datetime import datetime
import argparse
from tqdm import tqdm
from PIL import Image, UnidentifiedImageError

def get_exif_date(image_path):
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if exif_data:
            date_str = exif_data.get(36867)
            if date_str:
                return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
    except UnidentifiedImageError:
        pass
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
    finally:
        img.close()
    return None

def get_filesystem_date(image_path):
    try:
        stat = os.stat(image_path)
        return datetime.fromtimestamp(stat.st_mtime)
    except Exception as e:
        print(f"Error accessing filesystem date for {image_path}: {e}")
        return None

def sort_images(source_dir, dest_dir, dry_run=False):
    image_paths = [os.path.join(dp, f) for dp, dn, filenames in os.walk(source_dir) for f in filenames if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
    
    for image_path in tqdm(image_paths, desc="Sorting Images"):
        date = get_exif_date(image_path) or get_filesystem_date(image_path)
        
        if date:
            new_dir = os.path.join(dest_dir, f"{date.year}/{date.month:02}")
            if not dry_run:
                os.makedirs(new_dir, exist_ok=True)
                shutil.move(image_path, os.path.join(new_dir, os.path.basename(image_path)))
            print(f"Dry Run: Moving {image_path} to {os.path.join(new_dir, os.path.basename(image_path))}" if dry_run else f"Moving {image_path} to {os.path.join(new_dir, os.path.basename(image_path))}")

def main():
    parser = argparse.ArgumentParser(description="Sort images by date into folders.")
    parser.add_argument("source_dir", help="Source directory containing images to sort.")
    parser.add_argument("dest_dir", help="Destination directory to store sorted images.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate the sorting process without moving any files.")
    
    args = parser.parse_args()
    
    sort_images(args.source_dir, args.dest_dir, args.dry_run)

if __name__ == "__main__":
    main()
