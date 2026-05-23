from setuptools import find_packages, setup


setup(
    name="yandex-metrika-api",
    version="0.1.0",
    description="Small Python client for loading reports from Yandex Metrica API.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Ivan Bibanin",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "pandas>=1.5",
        "requests>=2.25",
    ],
)
