"""Monitor a package for changes and run its tests when it changes."""

import time
from .assertion import rerun_failing_assert
from .importation import import_module, get_directory_of
from .launch import launch_sync

def main_loop(name):
    """Survive hard import errors, like SyntaxError, and try again forever."""
    while True:
        # try:
        watch_loop(name)
        # except Exception as e:
        #     print('Fatal: {}'.format(e))
        #     print('Edit your code and Assay will try again')
        break
        time.sleep(100000)

def watch_loop(module_name):
    path = launch_sync(get_directory_of, module_name)
    if path is not None:
        raise NotImplementedError('cannot yet introspect full packages')
    data = launch_sync(run_tests_of, module_name)
    print data

def run_tests_of(name):
    module = import_module(name)
    d = module.__dict__
    good_names = sorted(k for k in d if k.startswith('test_'))
    candidates = [d[k] for k in good_names]
    tests = [t for t in candidates if t.__module__ == name]
    print '-' * 72
    for t in tests:
        if t.func_code.co_argcount:
            continue
        try:
            t()
        except AssertionError as e:
            rerun_failing_assert(t)
        except Exception as e:
            print
            print t.__name__
            print e.__class__.__name__, e
    return len(tests)
    for tn in test_names:
        test = d[tn]
        print(test.__module__)
    return []
    names = []
    for name, obj in vars(module).items():
        if not name.startswith('test_'):
            continue
        names.append(name)
    return names
