"""Workarounds for Python 3."""

import sys

# I'm fortunate that Mercurial ran into this issue before Assay did:
# they figured out both how to reproduce the problem and how to fix it!
# See `notes/pickling-fix.txt` in the Assay repository for details.

if sys.version_info[0] == 3:
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
        if sys.version_info[1] == 8:
            def readinto(): raise NotImplementedError()

else:
    def _accumulating_reader(pipe):
        return pipe
