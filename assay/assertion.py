"""Routines to deal with the Python assert statement."""

import dis
import re
import types
from sys import version_info
from types import FunctionType
from .compatibility import get_code, set_code, unittest

_case = unittest.TestCase('setUp')
_case.maxDiff = 2048  # TODO: people should be able to customize this
_python_version = version_info[:2]
fancy_comparisons = {
    '<': _case.assertLess,
    '<=': _case.assertLessEqual,
    '==': _case.assertEqual,
    '!=': _case.assertNotEqual,
    '>': _case.assertGreater,
    '>=': _case.assertGreaterEqual,
    'in': _case.assertIn,
    'not in': _case.assertNotIn,
    'is': _case.assertIs,
    'is not': _case.assertIsNot,
    'exception match': _case.assertIsInstance,
    'BAD': None,
}

operator_constants = tuple(fancy_comparisons[op] for op in dis.cmp_op)

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
        ])

elif _python_version <= (3,8):

    assert_pattern_text = assemble_pattern([
        op.compare_op, b'(.)',
        b'(?:', op.extended_arg, b'.)?',
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

else:

    assert_pattern_text = assemble_pattern([
        op.compare_op, b'(.)',
        b'(?:', op.extended_arg, b'.)?',
        op.pop_jump_if_true, b'.',
        op.load_assertion_error, b'.',
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
        # TODO: if there's a second group in the match, should we verify
        # that it really loads `AssertionError`?
        compare_op = match.group(1)
        if _python_version <= (3,5):
            msb, lsb = divmod(offset + ord(compare_op), 256)
            code = replacement.replace(b'%%', chr(lsb) + chr(msb))
        else:
            code = replacement.replace(b'%%', chr(offset + ord(compare_op)))
        short = len(match.group(0)) - len(code)
        if short:
            code += chr(op.nop) * short
        return code

    c = get_code(function)
    offset = len(c.co_consts)
    newcode = assert_pattern.sub(replace, c.co_code)
    code_object = code_object_replace(
        c,
        new_code=newcode,
        new_consts=c.co_consts + operator_constants,
        new_stacksize=c.co_stacksize + 1,
    )
    set_code(function, code_object)

def code_object_replace(c, new_code, new_consts, new_stacksize):
    """Emulate `.replace()` method for code objects in older Pythons."""
    if _python_version >= (3,8):
        return c.replace(
            co_code=new_code,
            co_consts=new_consts,
            co_stacksize=new_stacksize,
        )
    args = (
        c.co_argcount,
        c.co_nlocals,
        new_stacksize,
        c.co_flags,
        new_code,
        new_consts,
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
    return types.CodeType(*args)

def search_for_function(code, candidate, frame, name):
    """Find the function whose code object is `code`, else return None."""
    if get_code(candidate) is code:
        return candidate
    candidate = frame.f_locals.get(name) or frame.f_globals.get(name)
    if isinstance(candidate, FunctionType):
        if get_code(candidate) is code:
            return candidate
    return None
