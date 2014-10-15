"""Routines to deal with the Python assert statement."""

import dis
import sys
import types

python3 = (sys.version_info.major >= 3)

class op(object):
    """Op code symbols."""

for i, symbol in enumerate(dis.opname):
    setattr(op, symbol.lower(), i)

class CompareError(Exception):
    def __init__(self, a, b, symbol):
        self.symbol = symbol
        self.a = a
        self.b = b

additional_consts = dis.cmp_op + (CompareError,)
real_bytes = bytes

def rerun_failing_assert(test, code):
    dis.dis(code)

    original_code = code.co_code

    if isinstance(original_code, str):
        bytes = [ord(b) for b in original_code]  # Python 2
    else:
        bytes = list(original_code)              # Python 3

    consts = code.co_consts
    cmp_base = len(consts)
    consts = consts + additional_consts
    # error_index = code.co_names.index('AssertionError')
    # error_lsb, error_msb = divmod(error_index, 256)
    exception_msb, exception_lsb = divmod(consts.index(CompareError), 256)
    stacksize = code.co_stacksize + 2

    i = 0
    original_length = len(bytes)

    while i < original_length:
        if bytes[i] == op.compare_op:
            i += 3
            if bytes[i] == op.pop_jump_if_true:
                i += 3
                if bytes[i] == op.load_global:  # TODO: check global
                    i += 3
                    if bytes[i] == op.raise_varargs:
                        i += 3
                        print('*'*20, len(bytes))
                        insert_handler(bytes, i - 12, cmp_base,
                                       exception_lsb, exception_msb)
                        print('*'*20, len(bytes))
        else:
            i += 1 if (bytes[i] < dis.HAVE_ARGUMENT) else 3

    #new_code

    c = code

    new_code = real_bytes(bytes) if python3 else ''.join(
        chr(byte) for byte in bytes)

    print(repr(new_code))

    #    argcount, kwonlyargcount, nlocals, stacksize, flags, codestring,
    # |        constants, names, varnames, filename, name, firstlineno,
    # |        lnotab[, freevars[, cellvars]])
    if python3:
        argcounts = (c.co_argcount, c.co_kwonlyargcount)
    else:
        argcounts = (c.co_argcount,)
    # print((
    #     c.co_argcount, c.co_nlocals, stacksize, c.co_flags, new_code,
    #     consts, c.co_names, c.co_varnames, c.co_filename, c.co_name,
    #     c.co_firstlineno, c.co_lnotab, c.co_freevars, c.co_cellvars))

    new_func_code = types.CodeType(*argcounts + (
        c.co_nlocals, stacksize, c.co_flags, new_code, consts, c.co_names,
        c.co_varnames, c.co_filename, c.co_name, c.co_firstlineno, c.co_lnotab,
        c.co_freevars, c.co_cellvars))
    if python3:
        test.__code__ = new_func_code
    else:
        test.func_code = new_func_code

    dis.dis(test)

    try:
        test()
    except CompareError as e:
        return 'BUT {!r}\n   {} {!r}'.format(e.a, e.symbol, e.b)
    else:
        return 'drat, no exception was raised the second time'

def insert_handler(bytes, i, cmp_base, exception_lsb, exception_msb):
    """The index `i` should point at the COMPARE_OP of an assert."""

    base = len(bytes)
    operator = bytes[i+1]
    jump_back_lsb = bytes[i+4]
    jump_back_msb = bytes[i+5]

    jump_to_handler_msb, jump_to_handler_lsb = divmod(base, 256)
    bytes[i:i+3] = [op.jump_absolute, jump_to_handler_lsb, jump_to_handler_msb]

    reporting_msb, reporting_lsb = divmod(base + 14 - 2 * python3, 256)
    symbol_msb, symbol_lsb = divmod(cmp_base + operator, 256)

    # Duplicate the two operands of "compare_op" then do comparison.

    bytes.extend(
        [op.dup_top_two] if python3 else [op.dup_topx, 2, 0]
        )
    bytes.extend([
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
