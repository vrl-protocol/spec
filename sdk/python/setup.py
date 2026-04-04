"""Setup configuration for VRL SDK package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="vrl-sdk",
    version="0.1.4",
    author="Verifiable Reality Layer Contributors",
    author_email="info@vrl.io",
    description="Python SDK for the Verifiable Reality Layer (VRL) Proof Bundle Specification v1.0",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vrl-protocol/spec",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=22.0",
            "flake8>=4.0",
            "mypy>=0.950",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering",
        "Topic :: Security :: Cryptography",
    ],
    keywords="vrl verifiable reality layer proof bundle cryptography zk zero-knowledge",
    project_urls={
        "Bug Reports": "https://github.com/vrl-protocol/spec/issues",
        "Source": "https://github.com/vrl-protocol/spec",
        "Documentation": "https://vrl-protocol.github.io/spec",
    },
)
