import pkg_resources


def get_license_txt(pkg):
    if pkg.has_metadata("LICENSE"):
        lic = pkg.get_metadata("LICENSE")
    else:
        lic = "(license detail not found)"
    return lic


def get_info(name, lines):
    """
    Search information in a list of lines.
    The expected format of the line is "name: info"
    This function search the name and return the info.

    :param name: name to be search at the beginning of a line.
    :param lines: list of strings.
    :return: the info part of the line for the given name.
    """
    sep = name + ": "
    for line in lines:
        if line.startswith(sep):
            return line.split(sep, maxsplit=1)[1]
    return f"({name} not found)"


def get_main_info(pkg):
    """
    Get information from libraries.

    :param pkg: a package object from pkg_resources.working_set
    :return: a dict with library, license, version, author, description and home page.
    """
    lines1 = []
    lines2 = []
    # Find info in metadata
    if pkg.has_metadata("METADATA"):
        lines1 = pkg.get_metadata_lines("METADATA")
    # find info in PKG-INFO
    if pkg.has_metadata("PKG-INFO"):
        lines2 = pkg.get_metadata_lines("PKG-INFO")
    # Transform lines into list
    lines = [l for l in lines1] + [l for l in lines2]

    # Manage case where license is UNKNOWN
    lic = get_info("License", lines)
    if lic == "UNKNOWN":
        lic = get_info("Classifier: License :", lines)
    return {
        "library": get_info("Name", lines),
        "license": lic,
        "version": get_info("Version", lines),
        "author": get_info("Author", lines),
        "description": get_info("Summary", lines),
        "home page": get_info("Home-page", lines),
    }


def get_licenses_summary():
    """
    Get a list of dicts with licenses and library information.

    :return: a list of dicts with library, license, version, author, description, home page and license text.
    """
    license_list = []
    for pkg in sorted(pkg_resources.working_set, key=lambda x: str(x).lower()):
        license_list += [
            {
                **get_main_info(pkg),
                "license_text": get_license_txt(pkg),
            }
        ]
    return license_list
