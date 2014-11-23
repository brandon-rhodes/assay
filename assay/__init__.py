"""A fast Python testing framework.

* When Assay sees an orphan .pyc file without a matching .py file, it
  should report an error.  This would prevent the user from thinking
  that they have successfully removed a module from their project when,
  in fact, their tests are only passing because of the old .pyc file.

"""
import re
import sys
from unittest.case import _AssertRaisesContext, TestCase

_python3 = sys.version_info >= (3,)
_throwaway_test_case = TestCase('setUp')

class raises(_AssertRaisesContext):
    """Context manager that verifies the exception its code block raises."""

    def __init__(self, expected, regex=None):
        f = _AssertRaisesContext.__init__
        if _python3:
            f(self, expected, _throwaway_test_case, expected_regex=regex)
        else:
            if isinstance(regex, str):
                regex = re.compile(regex)
            f(self, expected, _throwaway_test_case, expected_regexp=regex)

__all__ = ['raises']
