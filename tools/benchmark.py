from time import time
from assay.worker import Worker

def dot():
    return '.'

def main():
    worker = Worker()
    n = 2000
    items = [None] * n

    t0 = time()
    for item in items:
        assert worker.call(int) == 0
    dt = time() - t0

    print('{:,.6f} s = {:,.1f} /s: Using a worker to call a built-in'
          .format(dt / n, n / dt))

    t0 = time()
    for item in items:
        with worker:
            assert worker.call(int) == 0
    dt = time() - t0

    print('{:,.6f} s = {:,.1f} /s: Pushing, calling, then popping a new worker'
          .format(dt / n, n / dt))

    worker.close()

if __name__ == '__main__':
    main()
