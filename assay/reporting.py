"""Display test results and respond to user keystrokes."""

from __future__ import print_function

import sys
from time import time

stdout_fd = sys.stdout.fileno()
stdout_banner = ' stdout '.center(72, '-')
stderr_banner = ' stderr '.center(72, '-')
plain_banner = '-' * 72
help_hint = 'Press ? for help'
help_hint_length = len(help_hint)
help_message = """
 [j] Next error
 [k] Previous error
 [r] Restart Assay
 [q] Quit Assay
 [?] Help (this summary)
"""  # Future: [m] Pipe all errors to more(1) or else your custom $PAGER

class BatchReporter(object):
    def __init__(self, write_callback):
        self.write_callback = write_callback
        self.errors = 0
        self.tests = 0
        self.t0 = time()

    def report_result(self, result):
        self.tests += 1
        if result == '.':
            self.write_callback('.')
        else:
            self.errors += 1
            self.write_callback(pretty_format_error(*result))

    def summarize(self):
        dt = time() - self.t0
        if self.errors:
            tally = '{0} of {1} tests failed'.format(self.errors, self.tests)
        else:
            tally = 'All {0} tests passed'.format(self.tests)
        self.write_callback('\n\n{0} in {1:.2f} seconds\n'.format(tally, dt))


class InteractiveReporter(object):
    def __init__(self, write_callback):
        self.write_callback = write_callback
        self.letters = []
        self.errors = []
        self.error_index = 0
        self.column = 0
        self.period = 78 - help_hint_length
        self.t0 = time()

    def write(self, s):
        """Write out the string `s`, keeping track of the cursor column."""
        self.write_callback(s)
        i = s.rfind('\r')
        if i != -1:
            self.column = 0
            s = s[i+1:]
        self.column += len(s) - s.count('\033') // 2 * 11

    def report_result(self, result):
        is_success = (result == '.')
        letter = '.' if is_success else result[0]
        self.letters.append(letter)
        if not self.errors:
            if is_success:
                self.write('.')
                return
            self.write(pretty_format_error(*result))
            self.write(' ' * (79 - help_hint_length) + black(help_hint) + '\r')
        if not is_success:
            self.errors.append(result)
            self.write_error_count()
        if self.column >= self.period:
            self.write_error_count()
        self.write(letter)
        #self.write(''.join(self.letters[-72:]) + '\r')

    def write_error_count(self):
        c = self.error_index + 1
        message = 'Viewing {0} of {1} errors '.format(c, len(self.errors))
        self.write('\r' + black(message))

    def summarize(self):
        dt = time() - self.t0
        failures = len(self.errors)
        total = len(self.letters)
        if failures:
            tally = red('\r{0} of {1} tests failed'.format(failures, total))
        else:
            tally = green('\nAll {0} tests passed'.format(total))
        self.write('{0} in {1:.2f} seconds '.format(tally, dt))

    def process_keystroke(self, keystroke):
        if keystroke == b'?':
            self.write(help_message)
            return
        elif keystroke == b'j':
            if self.error_index + 1 >= len(self.errors):
                return
            self.error_index += 1
        elif keystroke == b'k':
            if not self.error_index:
                return
            self.error_index -= 1
        else:
            return

        self.write(pretty_format_error(*self.errors[self.error_index]))
        self.write(' ' * (79 - help_hint_length) + black(help_hint) + '\r')
        self.write_error_count()


def pretty_format_error(character, name, message, frames, out='', err=''):
    lines = ['']
    print = lines.append

    out = out.rstrip()
    err = err.rstrip()
    if out:
        lines.append(stdout_banner)
        print(green(out))
    if err:
        print(stderr_banner)
        print(yellow(err))
    if out or err:
        print(plain_banner)
    for tup in frames:
        filename, line_number, function_name, text = tup
        a = '  {0} line {1} in'.format(filename, line_number)
        b = '{0}'.format(function_name)
        f = '{0}\n  {1}' if (len(a) + len(b) > 78) else '{0} {1}'
        print(f.format(a, b))
        print(blue('    ' + text.replace('\n', '\n    ')))
    line = '{0}: {1}'.format(name, message) if message else name
    print(red(line))
    print('')

    return '\n'.join(lines)

def black(text): # ';47' does bg color
    return '\033[1;30m' + str(text) + '\033[0m'

def red(text):
    return '\033[1;31m' + str(text) + '\033[0m'

def green(text):
    return '\033[1;32m' + str(text) + '\033[0m'

def yellow(text):
    return '\033[1;33m' + str(text) + '\033[0m'

def blue(text):
    return '\033[1;35m' + str(text) + '\033[0m'
