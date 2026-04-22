import setuptools
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent

with open(ROOT / "README.rst", encoding="utf-8") as fh:
    long_description = fh.read()

with open(ROOT / "pyproject.toml", "rb") as fh:
    pyproject_data = tomllib.load(fh)

required = pyproject_data.get("project", {}).get("dependencies", [])

setuptools.setup(
    name="cornflow",
    version="1.3.1rc2",
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
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "cornflow = cornflow.cli:cli",
        ]
    },
)
