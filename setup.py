#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Setup script for JasmineTool
"""

import os
import sys
from setuptools import setup, find_packages

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as f:
        return f.read()

# Read the requirements from pyproject.toml or create a basic list
def read_requirements():
    """Read requirements from pyproject.toml or return basic dependencies"""
    requirements = [
        "pyyaml>=5.4.0",
        "pathlib2>=2.3.0;python_version<'3.4'",
    ]
    
    # Try to read from pyproject.toml if it exists
    try:
        import toml
        with open("pyproject.toml", "r") as f:
            pyproject_data = toml.load(f)
            project_deps = pyproject_data.get("project", {}).get("dependencies", [])
            if project_deps:
                requirements.extend(project_deps)
    except (ImportError, FileNotFoundError):
        pass
    
    return requirements

# Get version from __init__.py
def get_version():
    """Extract version from package __init__.py"""
    try:
        with open("src/jasminetool/__init__.py", "r") as f:
            for line in f:
                if line.startswith("__version__"):
                    return line.split("=")[1].strip().strip('"\'')
    except FileNotFoundError:
        pass
    return "0.1.0"

# Main setup configuration
setup(
    name="JasmineTool",
    version=get_version(),
    author="suchunsv",
    author_email="suchunsv@outlook.com",
    description="Automated multi-GPU/multi-host orchestration via SSH",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/Suchun-sv/JasmineTool",
    project_urls={
        "Bug Reports": "https://github.com/Suchun-sv/JasmineTool/issues",
        "Source": "https://github.com/Suchun-sv/JasmineTool",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.812",
        ],
        "docs": [
            "sphinx>=4.0",
            "sphinx-rtd-theme>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "jasminetool=jasminetool.cli:main",
            "jasmine-tool=jasminetool.cli:main",
            "jt=jasminetool.cli:main",
        ],
    },
    keywords="gpu ssh orchestration parallel wandb sweep distributed",
    include_package_data=True,
    zip_safe=False,
) 