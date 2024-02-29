"""Workarounds for Python 3."""

import sys
_python3 = sys.version_info >= (3,)

# We are extremely fortunate that Mercurial ran into this issue before
# assay did, as they figured out both how to reproduce the problem and
# how to fix it!

# https://phab.mercurial-scm.org/rHG12491abf93bd87b057cb6826e36606afa1cee88a
# https://phab.mercurial-scm.org/rHGc2bf211c74bf97be0a24e2446b75867cb4f588ee

# We are less fortunate that Mercurial's license isn't compatible with
# ours, as we must re-implement this rather than use their code.  But
# requiring us to re-implement is, after all, their right under the
# current copyright regime.

if _python3:
    class _accumulating_reader:
        def __init__(self, pipe):
            self._read = pipe.read
            self.readline = pipe.readline
            self.close = pipe.close

        def read(self, size=-1):
            read = self._read
            if size < 0:
                return read(-1)
            pieces = []
            while size:
                data = read(size)
                n = len(data)
                if not n:
                    break
                size -= n
                pieces.append(data)
            return b''.join(pieces)

        # Python 3.8 complains unless this method is present.
        def readinto(): raise NotImplementedError()

else:
    def _accumulating_reader(pipe):
        return pipe
