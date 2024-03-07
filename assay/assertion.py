"""Routines to deal with the Python assert statement."""

import dis
import re
import types
from sys import version_info
from types import FunctionType
from .compatibility import get_code, set_code, unittest

_python_version = version_info[:2]

# Turn bytecode opcodes into the attributes of a single object `op`, so
# we can write them conveniently like `op.compare_op`.

class op(object): pass
for i, symbol in enumerate(dis.opname):
    setattr(op, symbol.lower(), i)

# The master sequence of comparisons that we rewrite.  Their integer
# indexes are important, because indexes are how a function's bytecode
# reaches into its table of constants, which we will be extending with a
# block of methods in the same order as the comparisons are listed here.

comparison_names = (
    '<',
    '<=',
    '==',
    '!=',
    '>',
    '>=',
    'in',
    'not in',
    'is',
    'is not',
    'exception match',
)
comparison_indexes = {name: i for i, name in enumerate(comparison_names)}

# Figure out what each comparison will look like in bytecode, using the
# table of comparisons built-in to Python's `dis` module.

bytecode_map = {
    b'%c%c' % (op.compare_op, i): comparison_indexes[name]
    for i, name in enumerate(dis.cmp_op)
    if name != 'BAD'
}

# Recent Python versions have special opcodes for some comparisons.

if _python_version >= (3,9):
    bytecode_map[b'%c%c' % (op.contains_op, 0)] = comparison_indexes['in']

# Build a block of constants that offers a rich comparison method for
# each of the comparisons defined above.

_case = unittest.TestCase('setUp')
_case.maxDiff = 2048  # TODO: people should be able to customize this

comparison_constants = (
    _case.assertLess,
    _case.assertLessEqual,
    _case.assertEqual,
    _case.assertNotEqual,
    _case.assertGreater,
    _case.assertGreaterEqual,
    _case.assertIn,
    _case.assertNotIn,
    _case.assertIs,
    _case.assertIsNot,
    _case.assertIsInstance,
)

# How to assemble regular expressions and replacement strings.

if _python_version >= (3,0):
    def chr(n):
        return bytes((n,))

def assemble_replacement(things):
    return b''.join((t if isinstance(t, bytes) else chr(t)) for t in things)

def assemble_pattern(things):
    return b''.join((t if isinstance(t, bytes) else re.escape(chr(t)))
                    for t in things)

# Assemble a regular expression pattern for each comparison.

operator_patterns = {
    assemble_pattern(pattern) for pattern in bytecode_map
}

# How an "assert" statement looks in each version of Python.

if _python_version <= (3,5):

    assert_pattern_text = assemble_pattern([
        b'(', b'|'.join(operator_patterns), b')', 0,
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
        b'(', b'|'.join(operator_patterns), b')',
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
        b'(', b'|'.join(operator_patterns), b')',
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
        comparison_bytecode = match.group(1)
        comparison_index = bytecode_map[comparison_bytecode]
        if _python_version <= (3,5):
            msb, lsb = divmod(offset + comparison_index, 256)
            code = replacement.replace(b'%%', chr(lsb) + chr(msb))
        else:
            code = replacement.replace(b'%%', chr(offset + comparison_index))
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
        new_consts=c.co_consts + comparison_constants,
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
