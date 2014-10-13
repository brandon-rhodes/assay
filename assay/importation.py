"""Routines that understand Python importation."""

from importlib import import_module

def get_directory_of(name):
    """Return the base directory of a package, or None for a plain module."""
    module = import_module(name)
    return getattr(module, '__path__', None)
