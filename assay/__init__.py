"""A fast Python testing framework.

* When Assay sees an orphan .pyc file without a matching .py file, it
  reports an error.  This prevents the user from thinking that they have
  successfully removed a module from their project when, in fact, their
  tests are only passing because of the old .pyc file.

"""

import re
from unittest.case import _AssertRaisesContext

class raises(_AssertRaisesContext):
    """Context manager that verifies the exception its code block raises."""

    def __init__(self, expected, expected_regexp=None):
        self.expected = expected
        self.failureException = AssertionError
        self.expected_regexp = re.compile(expected_regexp)

__all__ = ['raises']
