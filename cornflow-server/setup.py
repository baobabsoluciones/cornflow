import setuptools

with open("README.rst") as fh:
    long_description = fh.read()

required = []
with open("requirements.txt", "r") as fh:
    required.append(fh.read().splitlines())

setuptools.setup(
    name="cornflow",
    version="1.2.2",
    author="baobab soluciones",
    author_email="cornflow@baobabsoluciones.es",
    description="cornflow is an open source multi-solver optimization server with a REST API built using flask.",
    long_description=long_description,
    url="https://github.com/baobabsoluciones/cornflow",
    packages=setuptools.find_packages(),
    install_requires=required,
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "cornflow = cornflow.cli:cli",
        ]
    },
)
