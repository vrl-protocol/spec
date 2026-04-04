"""Setup configuration for VRL SDK package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="vrl-sdk",
        version="0.1.1",
    author="Verifiable Reality Layer Contributors",
    author_email="info@vrl.io",
    description="Python SDK for the Verifiable Reality Layer (VRL) Proof Bundle Specification v1.0",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vrl-protocol/sdk-python",
    license="CC BY 4.0",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        # stdlib only + cryptography (optional, for future TEE verification)
    ],
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
        "License :: OSI Approved :: Creative Commons Attribution 4.0 International",
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
        "Bug Reports": "https://github.com/vrl-protocol/sdk-python/issues",
        "Source": "https://github.com/vrl-protocol/sdk-python",
        "Documentation": "https://vrl.io/docs",
    },
)
