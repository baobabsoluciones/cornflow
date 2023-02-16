import setuptools

# with open("README.rst") as fh:
#     long_description = fh.read()

required = []
with open("requirements.txt", "r") as fh:
    required.append(fh.read().splitlines())

setuptools.setup(
    name="cornflow",
    version="1.0.0a7",
    author="baobab soluciones",
    author_email="sistemas@baobabsoluciones.es",
    url="http://github.com/baobabsoluciones/cornflow",
    packages=setuptools.find_packages(),
    install_requires=required,
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "cornflow = cornflow.cli:cli",
        ]
    },
)
