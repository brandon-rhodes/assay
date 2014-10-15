"""Routines to deal with the Python assert statement."""

import dis
import types

class op(object):
    """Op code symbols."""

for i, symbol in enumerate(dis.opname):
    setattr(op, symbol.lower(), i)

# compare_op = opmap['COMPARE_OP']
# pop_jump_if_true = opmap['POP_JUMP_IF_TRUE']
# load_global = opmap['LOAD_GLOBAL']
# jump_absolute = opmap['JUMP_ABSOLUTE']
# raise_varargs = opmap['RAISE_VARARGS']

def rerun_failing_assert(test, code):
    dis.dis(code)

    print type(code)
    if isinstance(code.co_code, str):
        bytes = [ord(b) for b in code.co_code]  # Python 2
    else:
        bytes = list(code.co_code)              # Python 3
    print bytes

    error_index = code.co_names.index('AssertionError')
    error_lsb, error_msb = divmod(error_index, 256)

    i = 0
    original_length = len(bytes)

    while i < original_length:
        if bytes[i] == op.compare_op:
            i += 3
            if bytes[i] == op.pop_jump_if_true:
                i += 3
                if bytes[i] == op.load_global:
                    i += 3
                    if bytes[i] == op.raise_varargs:
                        i += 3
                        insert_handler(bytes, i - 12, error_lsb, error_msb)
        else:
            i += 1 if (bytes[i] < dis.HAVE_ARGUMENT) else 3

    #new_code

    c = code
    print bytes
    new_code = ''.join(chr(byte) for byte in bytes)
    new_func_code = types.CodeType(
        c.co_argcount, c.co_nlocals, c.co_stacksize, c.co_flags, new_code,
        c.co_consts, c.co_names, c.co_varnames, c.co_filename, c.co_name,
        c.co_firstlineno, c.co_lnotab, c.co_freevars, c.co_cellvars)
    test.func_code = new_func_code

    print('-------')
    dis.dis(test)
    print('-------')
    a, b = test()
    return 'BUT {!r}\n   != {!r}'.format(a, b)

def insert_handler(bytes, i, error_lsb, error_msb):
    """The index `i` should point at the COMPARE_OP of an assert."""

    base = len(bytes)
    operator = bytes[i+1]
    jump_lsb = bytes[i+4]
    jump_msb = bytes[i+5]

    msb, lsb = divmod(base, 256)
    bytes[i:i+3] = [op.jump_absolute, lsb, msb]

    msb, lsb = divmod(base + 14, 256)  # assertion handler offset; see below
    bytes.extend([

        # Duplicate the two operands of "compare_op" then do comparison.

        op.dup_topx, 2, 0,
        op.compare_op, operator, 0,
        op.pop_jump_if_false, lsb, msb,

        # If it worked, remove the two extra copies and restore control.

        op.pop_top,
        op.pop_top,
        op.jump_absolute, jump_lsb, jump_msb,

        # Otherwise, save the values in the exception (base + 14 points here).

        op.build_tuple, 2, 0,
        op.load_global, error_lsb, error_msb,
        op.raise_varargs, 2, 0,
        ])

def old():
    print(bytelist)

    if assert_eq not in code.co_code:
        print('CANNOT DO IT')
        return
    assert len(assert_eq) == len(return_eq)

    c = code
    new_code = c.co_code.replace(assert_eq, return_eq)
    new_func_code = types.CodeType(
        c.co_argcount, c.co_nlocals, c.co_stacksize, c.co_flags, new_code,
        c.co_consts, c.co_names, c.co_varnames, c.co_filename, c.co_name,
        c.co_firstlineno, c.co_lnotab, c.co_freevars, c.co_cellvars)
    test.func_code = new_func_code
    a, b = test()
    return 'BUT {!r}\n   != {!r}'.format(a, b)
