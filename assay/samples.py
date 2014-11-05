"""Sample tests for the Assay test suite.

Beware that the tests examine tracebacks that include line numbers, and
are therefore sensitive to the exact line numbers of these functions.

"""
def test_passing():
    pass

def test_exc():
    raise Exception('xyz')

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
