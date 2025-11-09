from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    if os.path.exists("README.md"):
        with open("README.md", "r", encoding="utf-8") as f:
            return f.read()
    return "IMOS: Memory OS for Solo Professionals"

setup(
    name="imos",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "typer>=0.9.0",
        "requests>=2.28.0", 
        "numpy>=1.21.0",
        "sentence-transformers>=2.2.0",
        "python-dotenv>=0.19.0",
        "PyMuPDF>=1.20.0",  # for PDF support (fitz)
        "python-docx>=0.8.11",  # for DOCX support
        "torch>=1.12.0",  # Required by sentence-transformers
        "transformers>=4.20.0",  # Required by sentence-transformers
    ],
    entry_points={
        "console_scripts": [
            "imos=imos.main:main_cli",
        ],
    },
    author="IMOS Team",
    author_email="support@imos.dev",
    description="IMOS: Memory OS for Solo Professionals - Your thoughtful local memory assistant",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/Sumitagarwal-i/IMOS_terminal",
    project_urls={
        "Bug Reports": "https://github.com/Sumitagarwal-i/IMOS_terminal/issues",
        "Source": "https://github.com/Sumitagarwal-i/IMOS_terminal",
        "Documentation": "https://github.com/Sumitagarwal-i/IMOS_terminal#readme",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Office/Business :: Office Suites",
        "Topic :: Text Processing :: General",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    python_requires=">=3.8",
    keywords="memory assistant cli productivity knowledge management ai chat",
    license="MIT",
)