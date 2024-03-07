"""Sample tests for the Assay test suite to exercise."""

from assay import assert_raises

flags = set()

def mul(a, b):
    return a * b

def test_passing():
    pass

def test_assert0():
    assert False

def test_assert1():
    assert 1+1 == 2+2

def sub_assert2():
    assert 2+2 == 3+3

def test_assert2():
    sub_assert2()

def test_assert3():
    f = int
    n = f()+0+1+2+3+4+5+6+7+8+9+0+1+2+3+4+5+6+7+8+9+0+1+2+3+4+5+6+7+8+9
    n += f()+0+1+2+3+4+5+6+7+8+9+0+1+2+3+4+5+6+7+8+9+0+1+2+3+4+5+6+7+8+9
    assert n == 100

def test_assert_tab():
    assert	1+1 == 3

def test_assert_then_pass():
    if 'a' not in flags:
        flags.add('a')
        assert 1+1 == 3

def test_assert_then_die():
    if 'b' not in flags:
        flags.add('b')
        assert 1+1 == 3
    raise ValueError('bad value')

def test_exc():
    raise OSError('xyz')

def test_exc2():
    return test_exc()

def test_fix0(fix0):
    assert fix0 < 2

def test_fix1(fix1):
    assert fix1 < 2

fix1 = None

def test_fix2(fix2):
    assert fix2 != 2

fix2 = [0, 1, 2, 3]

def test_fix3(fix3):
    assert fix3 != 1

def fix3():
    yield 0
    yield 1
    raise ValueError('xyz')
    yield 2

def test_fix4(test_exc):
    pass

def test_syntax_error():
    eval('1+2!3')

def test_raises1():
    with assert_raises(ValueError):
        raise ValueError('irrelevant message')

def test_raises2():
    with assert_raises(ValueError, 'correct message'):
        raise ValueError('correct message')

def test_raises3():
    with assert_raises(ValueError, 'correct message but wrong exception'):
        raise KeyError('correct message but wrong exception')

def test_raises4():
    with assert_raises(ValueError, 'one message'):
        raise ValueError('another message')

# We use the same order here that dis.cmp_op used in old versions of Python:
# ('<', '<=', '==', '!=', '>', '>=',
#  'in', 'not in', 'is', 'is not', 'exception match', 'BAD')

def test_lt():
    assert 3+4 < 1+2

def test_le():
    assert 3+4 <= 1+2

def test_eq():
    assert 1+2 == 3+4

def test_ne():
    assert 1+2 != 0+3

def test_gt():
    assert 1+2 > 3+4

def test_ge():
    assert 1+2 >= 3+4

def test_in():
    assert 1 in ()
