from setuptools import find_packages, setup

setup(
    name="psmovebridge",
    version="0.1.0",
    description="Asynchronous Python client and OpenTrack UDP bridge for PSMoveServiceEx.",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "protobuf>=3.20.0",
    ],
    python_requires=">=3.8",
)