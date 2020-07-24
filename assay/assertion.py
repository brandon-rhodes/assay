"""Routines to deal with the Python assert statement."""

import bdb
import dis
import operator
import re
import types
from sys import version_info
from types import FunctionType
from .compatibility import get_code, set_code, unittest

_case = unittest.TestCase('setUp')
_case.maxDiff = 2048  # TODO: people should be able to customize this
_python_version = version_info[:2]
fancy_comparisons = {
    '==': _case.assertEqual,
    'in': _case.assertIn,
    'not in': _case.assertNotIn,
    'is': _case.assertIs,
    'is not': _case.assertIsNot,
    }

plain_comparisons = {
    '<': operator.__lt__,
    '<=': operator.__le__,
    '!=': operator.__ne__,
    '>': operator.__gt__,
    '>=': operator.__ge__,
    'exception match': isinstance,  # no idea whether this is correct
    'BAD': None,
    }

def make_comparer(op):
    if op in fancy_comparisons:
        return fancy_comparisons[op]
    def compare(a, b):
        if not test(a, b):
            message = '{0!r}\n{1:>15} {2!r}'.format(a, 'is not ' + op, b)
            raise AssertionError(message)
    test = plain_comparisons[op]
    return compare

operator_constants = tuple(make_comparer(op) for op in dis.cmp_op)

class op(object):
    """Op code symbols."""

for i, symbol in enumerate(dis.opname):
    setattr(op, symbol.lower(), i)

# How to assemble regular expressions and replacement strings.

if _python_version >= (3,0):
    def chr(n):
        return bytes((n,))

def assemble_replacement(things):
    return b''.join((t if isinstance(t, bytes) else chr(t)) for t in things)

def assemble_pattern(things):
    return b''.join((t if isinstance(t, bytes) else re.escape(chr(t)))
                    for t in things)

# How an "assert" statement looks in each version of Python.

if _python_version <= (2,6):

    assert_pattern_text = assemble_pattern([
        op.compare_op, b'(.)', 0,
        op.jump_if_true, b'..',
        op.pop_top,
        op.load_global, b'(..)',
        op.raise_varargs, 1, 0,
        op.pop_top,
        ])

    replacement = assemble_replacement([
        op.load_const, b'%%',   # stack: ... op1 op2 function
        op.rot_three,           # stack: ... function op1 op2
        op.call_function, 2, 0, # stack: ... return_value
        op.nop, op.nop, op.nop, op.nop, op.nop, op.nop,
        op.pop_top,             # stack: ...
        ])

elif _python_version <= (3,5):

    assert_pattern_text = assemble_pattern([
        op.compare_op, b'(.)', 0,
        op.pop_jump_if_true, b'..',
        op.load_global, b'(..)',
        op.raise_varargs, 1, 0,
        ])

    replacement = assemble_replacement([
        op.load_const, b'%%',   # stack: ... op1 op2 function
        op.rot_three,           # stack: ... function op1 op2
        op.call_function, 2, 0, # stack: ... return_value
        op.pop_top,             # stack: ...
        op.nop, op.nop, op.nop, op.nop,
        ])

else:

    assert_pattern_text = assemble_pattern([
        op.compare_op, b'(.)',
        op.pop_jump_if_true, b'.',
        op.load_global, b'(.)',
        op.raise_varargs, 1,
        ])

    replacement = assemble_replacement([
        op.load_const, b'%%',   # stack: ... op1 op2 function
        op.rot_three, 0,        # stack: ... function op1 op2
        op.call_function, 2,    # stack: ... return_value
        op.pop_top, 0,          # stack: ...
        ])

# Note that "re.S" is crucial when compiling this pattern, as a byte we
# are trying to match with "." might happen to have the numeric value of
# an ASCII newline.
assert_pattern = re.compile(assert_pattern_text, re.S)

def rewrite_asserts_in(function):

    def replace(match):
        match.group(2) # TODO: make sure this is the right symbol
        compare_op = match.group(1)
        if _python_version <= (3,5):
            msb, lsb = divmod(offset + ord(compare_op), 256)
            code = replacement.replace(b'%%', chr(lsb) + chr(msb))
        else:
            code = replacement.replace(b'%%', chr(offset + ord(compare_op)))
        return code

    c = get_code(function)
    offset = len(c.co_consts)
    newcode = assert_pattern.sub(replace, c.co_code)
    if _python_version >= (3,8):
        code_object = c.replace(
            co_code=newcode,
            co_consts=c.co_consts + operator_constants,
            co_stacksize=c.co_stacksize + 1,
        )
    else:
        args = (
            c.co_argcount,
            c.co_nlocals,
            c.co_stacksize + 1,
            c.co_flags,
            newcode,
            c.co_consts + operator_constants,
            c.co_names,
            c.co_varnames,
            c.co_filename,
            c.co_name,
            c.co_firstlineno,
            c.co_lnotab,
            c.co_freevars,
            c.co_cellvars,
        )
        if _python_version >= (3,0):
            args = args[0:1] + (c.co_kwonlyargcount,) + args[1:]
        code_object = types.CodeType(*args)
    set_code(function, code_object)

def search_for_function(code, candidate, frame, name):
    """Find the function whose code object is `code`, else return None."""
    if get_code(candidate) is code:
        return candidate
    candidate = frame.f_locals.get(name) or frame.f_globals.get(name)
    if isinstance(candidate, FunctionType):
        if get_code(candidate) is code:
            return candidate
    return None

class Debugger(bdb.Bdb):
    """Bring a function to its first breakpoint, then stop."""

    count = 0
    limit = None

    def user_line(self, frame):
        if not self.break_here(frame):
            self.set_continue()
            return
        count = self.count = self.count + 1
        limit = self.limit
        if (limit is not None) and (count >= limit):
            self.code = frame.f_code
            self.globals = frame.f_globals
            self.lasti = frame.f_lasti
            self.locals = frame.f_locals
            self.set_quit()
