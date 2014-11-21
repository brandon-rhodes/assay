"""Routines to deal with the Python assert statement."""

import dis
import sys
import types

python3 = (sys.version_info.major >= 3)

class op(object):
    """Op code symbols."""

for i, symbol in enumerate(dis.opname):
    setattr(op, symbol.lower(), i)

class AssayCompareError(Exception):
    def __init__(self, a, b, symbol):
        self.a = a
        self.b = b
        self.symbol = symbol

additional_consts = (AssayCompareError,) + dis.cmp_op

def rerun_failing_assert(test, code_object, args):
    """Re-run test() after rewriting its asserts for introspection."""

    c = code_object

    if python3:
        bytecode = list(c.co_code)
    else:
        bytecode = [ord(b) for b in c.co_code]

    try:
        i = c.co_names.index('AssertionError')
    except ValueError:
        return None
    assert_msb, assert_lsb = divmod(i, 256)

    consts = c.co_consts
    exception_msb, exception_lsb = divmod(len(consts), 256)
    cmp_base = len(consts) + 1
    consts = consts + additional_consts

    i = 0
    original_length = len(bytecode)

    load_assertion_error = [op.load_global, assert_lsb, assert_msb]

    while i < original_length:
        if bytecode[i] == op.compare_op:
            i += 3
            if bytecode[i] == op.pop_jump_if_true:
                i += 3
                if bytecode[i:i+3] == load_assertion_error:
                    i += 3
                    if bytecode[i] == op.raise_varargs:
                        i += 3
                        install_handler(bytecode, i - 12, cmp_base,
                                        exception_lsb, exception_msb)
        else:
            i += 1 if (bytecode[i] < dis.HAVE_ARGUMENT) else 3

    bytecode = bytes(bytecode) if python3 else ''.join(chr(b) for b in bytecode)
    stacksize = c.co_stacksize + 2

    if python3:
        argcounts = (c.co_argcount, c.co_kwonlyargcount)
    else:
        argcounts = (c.co_argcount,)

    new_func_code = types.CodeType(*argcounts + (
        c.co_nlocals, stacksize, c.co_flags, bytecode, consts, c.co_names,
        c.co_varnames, c.co_filename, c.co_name, c.co_firstlineno, c.co_lnotab,
        c.co_freevars, c.co_cellvars))

    if python3:
        test.__code__ = new_func_code
    else:
        test.func_code = new_func_code

    try:
        test(*args)
    except AssayCompareError as e:
        return 'it is false that {!r} {} {!r}'.format(e.a, e.symbol, e.b)
    except Exception:
        return None
    else:
        return None

def install_handler(bytecode, i, cmp_base, exception_lsb, exception_msb):
    """The index `i` should point at the COMPARE_OP of an assert."""

    base = len(bytecode)
    operator = bytecode[i+1]
    jump_back_lsb = bytecode[i+4]
    jump_back_msb = bytecode[i+5]

    jump_to_handler_msb, jump_to_handler_lsb = divmod(base, 256)
    bytecode[i:i+3] = [
        op.jump_absolute, jump_to_handler_lsb, jump_to_handler_msb
        ]

    reporting_msb, reporting_lsb = divmod(base + 14 - 2 * python3, 256)
    symbol_msb, symbol_lsb = divmod(cmp_base + operator, 256)

    # Duplicate the two operands of "compare_op" then do comparison.

    bytecode.extend(
        [op.dup_top_two] if python3 else [op.dup_topx, 2, 0]
        )
    bytecode.extend([
        op.compare_op, operator, 0,
        op.pop_jump_if_false, reporting_lsb, reporting_msb,

        # If it worked, remove the two extra copies and return control.

        op.pop_top,
        op.pop_top,
        op.jump_absolute, jump_back_lsb, jump_back_msb,

        # Otherwise, do reporting on the failed assertion.

        op.load_const, exception_lsb, exception_msb,
        op.rot_three,
        op.load_const, symbol_lsb, symbol_msb,
        op.call_function, 3, 0,
        op.raise_varargs, 1, 0,
        ])
