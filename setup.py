import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="s3shortlink",
    version="0.0.1",
    author="Paul Lucero",
    author_email="paul.lucero08@gmail.com",
    description="A small example package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/p-lucero/s3-shortlink",
    packages=setuptools.find_packages(),
    install_requires=[
        'boto3',
        'validators'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
