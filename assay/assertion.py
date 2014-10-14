"""Routines to deal with the Python assert statement."""

import types
# from dis import dis

# assert_eq = 'k\x02\x00s?\x00t\x03\x00\x82\x01\x00d\x00\x00S'
# return_eq = 'k\x02\x00s?\x00f\x02\x00S\x00\x00d\x00\x00S'

assert_eq = 'k\x02\x00s'
return_eq = 'f\x02\x00S'

def rerun_failing_assert(test):
    c = test.func_code
    if assert_eq not in c.co_code:
        print 'CANNOT DO IT'
        return
    assert len(assert_eq) == len(return_eq)
    new_code = c.co_code.replace(assert_eq, return_eq)
    new_func_code = types.CodeType(
        c.co_argcount, c.co_nlocals, c.co_stacksize, c.co_flags, new_code,
        c.co_consts, c.co_names, c.co_varnames, c.co_filename, c.co_name,
        c.co_firstlineno, c.co_lnotab, c.co_freevars, c.co_cellvars)
    test.func_code = new_func_code
    a, b = test()
    return 'BUT {!r}\n   != {!r}'.format(a, b)

"""
  1           0 LOAD_CONST               3 (2)
              3 LOAD_CONST               4 (4)
              6 BUILD_TUPLE              2
              9 RETURN_VALUE

d \x03 \x00
d \x04 \x00
f \x02 \x00
S

k \x02 \x00
s ? \x00
f \x02 \x00
S \x00 \x00
d \x00 \x00
S

             51 COMPARE_OP               2 (==)
             54 POP_JUMP_IF_TRUE        63
             57 LOAD_GLOBAL              3 (AssertionError)
             60 RAISE_VARARGS            1
        >>   63 LOAD_CONST               0 (None)
             66 RETURN_VALUE

t\x00\x00d\x01\x00d\n\x00\x83\x00\x01}\x00\x00|\x00\x00j\x01\x00\x83\x00\x00t\x02\x00d\x02\x00d\x03\x00d\x04\x00d\x05\x00d\x06\x00d\x08\x00d\t\x00\x83\x07\x00

k \x02 \x00
s ? \x00
t \x03 \x00
\x82 \x01 \x00
d \x00 \x00
S

"""
