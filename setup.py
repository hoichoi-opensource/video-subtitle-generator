from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="video-subtitle-system",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Production-grade video subtitle generation system using Vertex AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/video-subtitle-system",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "google-cloud-storage>=2.10.0",
        "google-cloud-aiplatform>=1.38.0",
        "vertexai>=1.38.0",
        "ffmpeg-python>=0.2.0",
        "PyYAML>=6.0.1",
        "tqdm>=4.66.1",
        "colorama>=0.4.6",
        "rich>=13.7.0",
        "click>=8.1.7",
        "opencv-python>=4.8.1.78",
        "moviepy>=1.0.3",
        "Pillow>=10.1.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "tenacity>=8.2.3",
        "pydantic>=2.5.2",
        "humanize>=4.8.0",
    ],
    entry_points={
        "console_scripts": [
            "videosub=scripts.main:main",
        ],
    },
)