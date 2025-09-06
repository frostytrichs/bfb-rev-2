#!/usr/bin/env python3
"""
Setup script for the Lemmy Bot package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="lemmy-bot",
    version="0.1.0",
    author="frostytrichs",
    author_email="author@example.com",  # Replace with actual email if desired
    description="A Python bot for interacting with Lemmy social media platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/frostytrichs/bfb-rev-2",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "lemmy-bot=src.__main__:main",
        ],
    },
)