import setuptools
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent

with open(ROOT / "README.rst", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open(ROOT / "pyproject.toml", "rb") as fh:
    pyproject_data = tomllib.load(fh)

required = pyproject_data.get("project", {}).get("dependencies", [])

extra_required = {"excel": ["openpyxl", "pandas"]}


setuptools.setup(
    name="cornflow-client",
    version="1.3.1rc1",
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
    python_requires=">=3.10",
    include_package_data=True,
    install_requires=required,
    extra_require=extra_required,
)
