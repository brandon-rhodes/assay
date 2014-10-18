"""Routines that understand Python importation."""

from importlib import import_module

def get_directory_of(name):
    """Return the base directory of a package, or None for a plain module."""
    module = import_module(name)
    return getattr(module, '__path__', None)

def improve_order(import_events):
    """Given an existing module `import_order` list, return a new one.

    The new import order learns from the `import_events` of the last
    slate of imports, a sequence whose tuples each report what really
    happened when a module name was imported:

    [('zlib', {'zlib'}),
     ('zipfile', {'_io', 'binascii', 'grp', 'io', 'pwd', 'shutil', 'zipfile'}),
     ...]

    New modules will be inserted into the import order just before the
    module that imports them.

    """
    imported_by = {b: a for a, bset in import_events for b in bset if a != b}
    already_appended = set()
    new_order = []

    def append(name):
        if name not in already_appended:
            already_appended.add(name)
            new_order.append(name)

    for module_name, names_imported in reversed(import_events):
        importer_name = imported_by.get(module_name)
        if importer_name is not None:
            append(importer_name)
        append(module_name)
        for name in sorted(names_imported, reverse=True):
            append(name)

    new_order.reverse()
    return new_order
