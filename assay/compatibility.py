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

__all__ = ['unittest']
