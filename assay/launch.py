"""Launch, manage, and stop workers with the greatest possible efficiency."""

import os

def launch_sync(function, *args, **kw):
    return function(*args, **kw)  # for now, for good tracebacks
    r, w = os.pipe()
    child_pid = os.fork()
    if not child_pid:
        os.close(r)
        result = function(*args, **kw)
        os.write(w, repr(result).encode('utf-8'))
        os.close(w)
        os._exit(0)
    os.close(w)
    data = os.read(r, 10000000)
    os.close(r)
    return eval(data)
