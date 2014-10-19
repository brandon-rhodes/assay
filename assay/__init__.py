"""A fast Python testing framework."""

import re
from unittest.case import _AssertRaisesContext

class raises(_AssertRaisesContext):
    """Context manager that verifies the exception its code block raises."""

    def __init__(self, expected, expected_regexp=None):
        self.expected = expected
        self.failureException = AssertionError
        self.expected_regexp = re.compile(expected_regexp)

__all__ = ['raises']
