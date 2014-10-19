"""A fast Python testing framework."""

# For the convenience of test code:

from unittest.case import _AssertRaisesContext

class raises(_AssertRaisesContext):
    """Context manager that verifies the exception its code block raises."""

    def __init__(self, expected, expected_regexp=None):
        self.expected = expected
        self.failureException = AssertionError
        print '****************', repr(expected_regexp)
        self.expected_regexp = expected_regexp

__all__ = ['raises']
