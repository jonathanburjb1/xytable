#!/usr/bin/env python3
"""
Setup script for X-Y Table Control System.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
install_requires = []
if requirements_path.exists():
    with open(requirements_path, "r", encoding="utf-8") as f:
        install_requires = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="xytable",
    version="0.1.0",
    description="X-Y Table Control System for Mesa 7I96S boards",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/xytable",
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "xytable=src.cli.main:cli",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Manufacturing",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Control",
        "Topic :: System :: Hardware",
    ],
    keywords="cnc, mesa, hardware, control, xy-table, servo",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/xytable/issues",
        "Source": "https://github.com/yourusername/xytable",
        "Documentation": "https://github.com/yourusername/xytable#readme",
    },
)
