from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="video-subtitle-generator",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Production-ready video subtitle generation system using Vertex AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/video-subtitle-generator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.9",
    install_requires=[
        "pyyaml>=6.0.1",
        "click>=8.1.7",
        "rich>=13.7.0",
        "colorlog>=6.8.0",
        "google-cloud-storage>=2.10.0",
        "google-cloud-aiplatform>=1.38.0",
        "vertexai>=1.38.0",
        "ffmpeg-python>=0.2.0",
    ],
    entry_points={
        "console_scripts": [
            "subtitle-generator=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.md", "*.sh"],
    },
)
