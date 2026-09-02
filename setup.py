from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="psmovebridge",
    version="0.1.0",
    author="Yohan Konan",
    description="Python client & 6DoF telemetry bridge for PSMoveServiceEx",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fullyohan/psmovebridge",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "protobuf>=3.20.0",
    ],
    python_requires=">=3.8",
)
