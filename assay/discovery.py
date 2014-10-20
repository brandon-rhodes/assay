"""Test discovery tools."""

import os
import re
from keyword import iskeyword
from .importation import import_modules, list_module_paths

def paths_and_modules(worker, names):
    """Return paths and modules for each name on the command line.

    Each name on the Assay command line can specify one of three things:
    a directory that contains .py files, the name of one particular .py
    file, or the name of a package that Python can import.  For every
    name provided in `names` this routine either reports an error to the
    user, or else yields a tuple (path, prefix) that will allow Python
    to import all of the Python files beneath the given name.

    """

def interpret_command_line_name(worker, name):
    if os.path.isdir(name):
        directory, prefix = os.path.abspath(name), ''
        while os.path.isfile(os.path.join(directory, '__init__.py')):
            parent, subdirectory = os.path.split(directory)
            if not subdirectory:
                print('Error: there should not be an __init__.py file'
                      ' at the root of your filesystem')
                return
            if not is_identifier(subdirectory):
                print('Error: {} contains an __init__.py file but {} is not'
                      ' a valid identifier'.format(parent, subdirectory))
                return
            directory, prefix = parent, subdirectory + '.' + prefix
        return directory, prefix

    if os.path.exists(name):
        base, extension = os.path.splitext(name)
        if extension != '.py':
            print('Error - test file lacks .py extension: {}'.format(name))
            return
        parent, module_name = os.path.split(base)
        return (parent or '.'), module_name

    with worker:
        worker(import_modules, [name])
        module_paths = dict(worker(list_module_paths))
    if name in module_paths:
        return None, name

    print('Error - can neither open nor import: {}'.format(name))

def is_identifier(name):
    return re.match('[A-Za-z_][A-Za-z0-9_]*', name) and not iskeyword(name)
