from setuptools import setup, find_packages

setup(
    name="yt-library-scraper",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "yt-dlp>=2024.03.10",
    ],
    entry_points={
        "console_scripts": [
            "yt-library=scraper.cli:main",
        ],
    },
    python_requires=">=3.8",
)
