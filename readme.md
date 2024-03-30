# Image Sorter

The Image Sorter script automates the organization of image files into folders based on the dates the images were taken. It supports sorting by EXIF date data when available, or by filesystem modification dates as a fallback.

## Features

- **EXIF Date Sorting**: Prefers image EXIF data for accuracy.
- **Filesystem Date Fallback**: Uses filesystem dates if EXIF data is unavailable.
- **Dry Run Mode**: Simulate file sorting without making any changes, for validation purposes.

## Prerequisites

- Python 3.x
- [Pillow](https://pillow.readthedocs.io/en/stable/) for handling image files and EXIF data.
- [tqdm](https://tqdm.github.io/) for progress bar visualization.

## Installation

1. Ensure Python 3.x is installed on your system.
2. Install the required Python packages:

```bash
pip install Pillow tqdm
```

## Usage

The script can be executed from the command line with the following syntax:

```bash
python image_sorter.py <source_dir> <dest_dir> [--dry-run]
```

- `<source_dir>`: The directory containing the images to be sorted.
- `<dest_dir>`: The directory where sorted images will be stored.
- `--dry-run` (optional): Simulates the sorting process without moving any files.

### Example

```bash
python image_sorter.py /path/to/images /path/to/sorted_images --dry-run
```

This command simulates sorting images from `/path/to/images` into `/path/to/sorted_images`.

## Contributing

Contributions to the Image Sorter script are welcome. Please feel free to report any issues or submit pull requests.

## License

This project is open-source and available under the MIT License.