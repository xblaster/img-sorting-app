# Image Sorter

The Image Sorter script automates the organization of image files into folders based on the dates the images were taken. It supports sorting by EXIF date data when available, or by filesystem modification dates as a fallback, with an additional option to categorize by a custom qualifier.

## Features

- **EXIF Date Sorting**: Prefers image EXIF data for accuracy.
- **Filesystem Date Fallback**: Uses filesystem dates if EXIF data is unavailable.
- **Qualifier Support**: Allows images to be sorted into sub-folders based on a user-defined qualifier.
- **Dry Run Mode**: Simulate file sorting without making any changes, for validation purposes.

## Prerequisites

- Python 3.x

## Installation

1. Clone the repository or download the project to your local machine.
2. Navigate to the project directory.
3. Install the required Python packages using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

This command will install all necessary dependencies, including Pillow for handling image files and EXIF data, and tqdm for progress bar visualization.

## Usage

The script can be executed from the command line with the following syntax:

```bash
python image_sorter.py <source_dir> <dest_dir> [--qualifier <qualifier>] [--dry-run]
```

- `<source_dir>`: The directory containing the images to be sorted.
- `<dest_dir>`: The directory where sorted images will be stored.
- `--qualifier <qualifier>` (optional): Specifies a sub-folder for additional categorization.
- `--dry-run` (optional): Simulates the sorting process without moving any files.

### Example

```bash
python image_sorter.py /path/to/images /path/to/sorted_images --qualifier event_name --dry-run
```

This command simulates sorting images from `/path/to/images` into `/path/to/sorted_images`, categorizing them under an `event_name` sub-folder.

## Contributing

Contributions to the Image Sorter script are welcome. Please feel free to report any issues or submit pull requests.

## License

This project is open-source and available under the MIT License.
