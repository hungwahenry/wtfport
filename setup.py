from setuptools import setup, find_packages
import os
from pathlib import Path

# Read the contents of your README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Get version from package without importing
about = {}
with open(os.path.join(this_directory, "wtfport", "version.py"), encoding="utf-8") as f:
    exec(f.read(), about)

# Core dependencies (copied from pyproject.toml)
requirements = [
    "typer>=0.7.0",
    "rich>=13.3.0",
    "psutil>=5.9.0",
    "pyperclip>=1.8.2",
    "plyer>=2.1.0",
    "colorama>=0.4.6",
    "wcwidth>=0.2.6",
    "requests>=2.28.2",
    "prompt_toolkit>=3.0.36"
]

# Development requirements
dev_requirements = [
    "pytest>=7.3.1",
    "tox>=4.5.1",
    "flake8>=6.0.0",
    "black>=23.3.0",
    "isort>=5.12.0",
]

setup(
    name="wtfport",
    version=about["__version__"],
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
    },
    entry_points={
        "console_scripts": [
            "wtfport=wtfport.cli:app",
        ],
    },

    # Metadata
    author="Hungwa Henry",
    author_email="henterhungwa@gmail.com",
    description="A terminal tool to identify, inspect, and interact with processes bound to specific ports",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="port, process, network, terminal, development, utilities, devtools",
    url="https://github.com/hungwahenry/wtfport",
    project_urls={
        "Bug Tracker": "https://github.com/hungwahenry/wtfport/issues",
        "Documentation": "https://github.com/hungwahenry/wtfport#readme",
        "Source Code": "https://github.com/hungwahenry/wtfport",
    },

    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Debuggers",
        "Topic :: System :: Networking",
        "Topic :: Utilities",
    ],
    python_requires=">=3.7",
    license="MIT",
)
