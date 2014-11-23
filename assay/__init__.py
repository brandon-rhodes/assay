"""A fast Python testing framework.

* When Assay sees an orphan .pyc file without a matching .py file, it
  should report an error.  This would prevent the user from thinking
  that they have successfully removed a module from their project when,
  in fact, their tests are only passing because of the old .pyc file.

"""
import re

class assert_raises(object):
    """Context manager that verifies the exception its code block raises."""

    def __init__(self, expected_type, pattern=None):
        self.expected_type = expected_type
        self.pattern = pattern

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, tb):
        if exception_type is None:
            complaint = '{0} not raised'.format(self.expected_type.__name__)
            raise AssertionError(complaint)
        if not issubclass(exception_type, self.expected_type):
            return False
        self.exception = exception
        pattern = self.pattern
        if (pattern is not None) and not re.search(pattern, str(exception)):
            complaint = 'cannot find pattern {0!r} in {1!r}'
            raise AssertionError(complaint.format(pattern, str(exception)))
        return True

__all__ = ['assert_raises']
