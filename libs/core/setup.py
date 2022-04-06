import setuptools

with open("README.rst") as fh:
    long_description = fh.read()

required = []
with open("requirements.txt", "r") as fh:
    required.append(fh.read().splitlines())

setuptools.setup(
    name="cornflow-core",
    version="0.0.1a9",
    author="baobab soluciones",
    author_email="sistemas@baobabsoluciones.es",
    description="REST API backend components used by cornflow and other REST APIs",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/baobabsoluciones/cornflow",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 2 - Pre-Alpha",
    ],
    python_requires=">=3.7",
    include_package_data=True,
    install_requires=required,
)
