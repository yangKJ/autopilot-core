from setuptools import setup, find_packages
from pathlib import Path

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="autopilot-core",
    version="0.1.0",
    description="🤖 通用自动驾驶模式 — 智能调度 + 学习预测 + 闭环自愈",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Condy",
    author_email="condy@example.com",
    url="https://github.com/packs/autopilot-core",
    license="MIT",
    packages=find_packages(),
    package_data={
        "autopilot_core": ["py.typed"],
        "autopilot_core.core": ["*.py"],
        "autopilot_core.mcp": ["*.py"],
        "autopilot_core.skills": ["**/*.py", "**/*.md", "**/scripts/*"],
    },
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "pyyaml",
    ],
    extras_require={
        "mcp": ["mcp>=0.1.0"],
        "dev": [
            "pytest>=7.0",
            "ruff>=0.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "autopilot=autopilot_core.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Quality Assurance",
    ],
    keywords="autopilot automation claude code cli learning engine",
)