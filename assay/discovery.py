"""Test discovery tools."""

import os
import re
import sys
from keyword import iskeyword
from .importation import get_directory_of, import_modules, list_module_paths

matches_dot_py = re.compile(r'[A-Za-z_][A-Za-z_0-9]*\.py$').match

def paths_and_modules(worker, names):
    """Return paths and modules for each name on the command line.

    Each name on the Assay command line can specify one of three things:
    a directory that contains .py files, the name of one particular .py
    file, or the name of a package that Python can import.  For every
    name provided in `names` this routine either reports an error to the
    user, or else yields a tuple (path, prefix) that will allow Python
    to import all of the Python files beneath the given name.

    """

def interpret_argument(worker, name):
    """

    ('/os/path/addition', '')  - search the directory itself
    ('/os/path/addition', 'name') - search module and its __path__ (if any)
    (None, 'name') - search module and its __path__ (if any)

    """
    if os.path.isdir(name):
        return _discover_enclosing_packages(name, [])

    if os.path.isfile(name):
        base, extension = os.path.splitext(name)
        if extension != '.py':
            print('Error - test file lacks .py extension: {0}'.format(name))
            return
        directory, name = os.path.split(base)
        return _discover_enclosing_packages(directory, [name])

    with worker:
        worker.call(import_modules, [name])
        module_paths = dict(worker.call(list_module_paths))
    if name in module_paths:
        return None, name

    print('Error - can neither open nor import: {0}'.format(name))

def search_argument(import_directory, import_name):
    """Given a tuple returned by `interpret_argument()`, find tests."""
    if import_directory is not None:
        sys.path.insert(0, import_directory)
    package_directory = get_directory_of(import_name)
    names = [import_name]
    if package_directory is not None:
        # TODO: make this recursive; tried to use os.walk(), but it looks
        # a bit awkward for this - makes us keep re-discovering where we are.
        # TODO: ignore subdirectories that cannot be package names?
        # Or that do not look test-like? Hmm. Big decisions there.
        for filename in os.listdir(package_directory):
            module_name = module_name_of(filename)
            if not module_name:
                continue
            names.append(import_name + '.' + module_name)
    return names

def search_plain_directory(directory, listing):
    possible_packages = []
    for filename in listing:
        module_name = module_name_of(filename)
        if module_name is not None:
            yield module_name, directory
        elif is_identifier(filename):
            possible_packages.append(filename)
    for filename in possible_packages:
        subdirectory = os.path.join(directory, filename)
        filenames = os.listdir(subdirectory)
        if '__init__.py' in filenames:
            asdf
        os.walk

def insert_path_and_search_package_or_module(path, name):
    sys.path.insert(0, path)
    return search_package_or_module(name)

def search_package_or_module(name):
    pass #import_module

def _discover_enclosing_packages(directory, names):
    """Find the top-level directory surrounding a package or sub-package."""
    was_absolute = directory.startswith(os.sep)
    directory = os.path.abspath(directory)
    while is_package(directory):
        directory, package_name = os.path.split(directory)
        if not package_name:
            print('Error - there should not be an __init__.py file'
                  ' at the root of your filesystem')
            return
        if not is_identifier(package_name):
            print('Error - directory contains an __init__.py but its'
                  ' name is not an identifier: {0}'.format(package_name))
            return
        names.append(package_name)
    if not was_absolute:
        directory = os.path.relpath(directory, '.')
    return directory or '.', '.'.join(reversed(names))

def is_package(directory):
    return os.path.isfile(os.path.join(directory, '__init__.py'))

def is_dot_py(name):
    return matches_dot_py(name) and not iskeyword(name[:-3])

def is_identifier(name):
    return re.match('[A-Za-z_][A-Za-z0-9_]*', name) and not iskeyword(name)

def module_name_of(filename):
    if matches_dot_py(filename):
        base = filename[:-3]
        if not iskeyword(base):
            return base
    return None
