from setuptools import setup, find_packages

setup(
    name="image_sorter",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # Your project's dependencies, as specified in requirements.txt
        # This can be dynamically loaded from requirements.txt as well
        "Pillow",
        "tqdm",
    ],
    entry_points={
        "console_scripts": [
            "image-sorter=image_sorter.sorter:main",  # Adjust according to your structure
        ],
    },
)