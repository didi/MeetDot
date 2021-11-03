import setuptools

setuptools.setup(
    name="streaming-speech-translation",
    version="0.0.1",
    author="DiDi Labs",
    python_requires=">=3.7",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
)
