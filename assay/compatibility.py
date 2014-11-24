"""Handle a few discrepancies."""

import sys

if sys.version_info >= (2, 7):
    import unittest
else:
    try:
        import unittest2 as unittest
    except ImportError:
        sys.stderr.write('ImportError: to enjoy Assay under Python 2.6,'
                         ' please install unittest2\n')
        sys.exit(2)

if sys.version_info >= (3,):
    def get_code(function):
        return function.__code__
    def set_code(function, code):
        function.__code__ = code
else:
    def get_code(function):
        return function.func_code
    def set_code(function, code):
        function.func_code = code

__all__ = ['unittest']
