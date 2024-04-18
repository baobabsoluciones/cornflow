import importlib.metadata as metadata


def get_info(name, pkg):
    """
    Search information in a package metadata.
    The expected format of the line is "name: info"
    This function searches for the name and returns the info.

    :param name: name to be searched.
    :param pkg: a dictionary representing the package metadata.
    :return: the info part of the line for the given name.
    """
    if name in pkg:
        return pkg[name]
    return f"({name} not found)"


def get_licenses_summary():
    """
    Get a list of dicts with licenses and library information.

    :return: a list of dicts with library, license, version, author, description, home page and license text.
    """
    license_list = []
    for pkg in sorted(metadata.distributions(), key=lambda x: x.metadata['Name'].lower()):
        pkg_metadata = dict(pkg.metadata.items())
        license_list += [
            {
                "library": get_info("Name", pkg_metadata),
                "license": get_info("License", pkg_metadata),
                "version": get_info("Version", pkg_metadata),
                "author": get_info("Author", pkg_metadata),
                "description": get_info("Summary", pkg_metadata),
                "home page": get_info("Home-page", pkg_metadata),
            }
        ]

    return license_list
