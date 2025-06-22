#!/usr/bin/env python3
"""
PKOS Linux Mirrorlist Manager Setup Script

Developer: Aamir Abdullah
Email: aamirabdullah33@gmail.com
License: Open Source
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="pkos-mirrorlist-manager",
    version="2.0.0",
    author="Aamir Abdullah",
    author_email="aamirabdullah33@gmail.com",
    description="A modern GUI application for managing Arch Linux mirror lists",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/pkos-linux/mirrorlist-manager",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Systems Administration",
        "Topic :: System :: Networking",
        "Environment :: X11 Applications :: Qt",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "pkos-mirrorlist-manager=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.desktop", "*.md", "LICENSE"],
    },
    data_files=[
        ("share/applications", ["pkos-mirrorlist-manager.desktop"]),
        ("share/doc/pkos-mirrorlist-manager", ["README.md", "LICENSE"]),
    ],
    keywords="mirror pacman arch linux pkos network repository gui",
    project_urls={
        "Bug Reports": "https://github.com/pkos-linux/mirrorlist-manager/issues",
        "Source": "https://github.com/pkos-linux/mirrorlist-manager",
        "Documentation": "https://wiki.pkos-linux.org",
    },
)