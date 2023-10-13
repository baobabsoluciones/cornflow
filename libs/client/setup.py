import setuptools

with open("README.rst", "r") as fh:
    long_description = fh.read()

required = []
with open("requirements.txt", "r") as fh:
    required.append(fh.read().splitlines())

extra_required = {"excel": ["openpyxl", "pandas"]}


setuptools.setup(
    name="cornflow-client",
    version="1.0.16a2",
    author="baobab soluciones",
    author_email="sistemas@baobabsoluciones.es",
    description="Client to connect to a cornflow server",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/baobabsoluciones/cornflow",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
    ],
    python_requires=">=3.8",
    include_package_data=True,
    install_requires=required,
    extra_require=extra_required,
)
