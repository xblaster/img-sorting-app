import unittest
from datetime import datetime
from tempfile import TemporaryDirectory
import os
from PIL import Image
from image_sorter.sorter import get_exif_date, get_filesystem_date, sort_images

class TestImageSorter(unittest.TestCase):

    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.source_dir = os.path.join(self.temp_dir.name, "source")
        self.dest_dir = os.path.join(self.temp_dir.name, "dest")
        os.makedirs(self.source_dir, exist_ok=True)
        os.makedirs(self.dest_dir, exist_ok=True)

        # Create a simple test image without EXIF data
        self.test_image_path = os.path.join(self.source_dir, "test_image.jpg")
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(self.test_image_path)

    def test_get_exif_date_none(self):
        # Verify that get_exif_date returns None for an image without EXIF data
        self.assertIsNone(get_exif_date(self.test_image_path), "Expected no EXIF date.")

    def test_get_filesystem_date(self):
        # Test get_filesystem_date with the created file
        expected_date = datetime.now()
        actual_date = get_filesystem_date(self.test_image_path)
        self.assertIsNotNone(actual_date, "Filesystem date should not be None.")
        # Allow for a few seconds difference due to filesystem timestamp resolution
        self.assertTrue(abs((expected_date - actual_date).total_seconds()) < 5, "Filesystem date should be close to the current time.")

    def test_sort_images_dry_run(self):
        # Test sort_images functionality in dry run mode
        sort_images(self.source_dir, self.dest_dir, dry_run=True)
        # Check that no files have been moved
        self.assertTrue(os.path.isfile(self.test_image_path), "Image should not be moved in dry run mode.")
        self.assertEqual(len(os.listdir(self.dest_dir)), 0, "Destination directory should be empty in dry run mode.")

    def tearDown(self):
        self.temp_dir.cleanup()

if __name__ == '__main__':
    unittest.main()
