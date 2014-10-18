import unittest
from .importation import improve_order

class AssayTests(unittest.TestCase):

    # We assume that module B imports A, C imports B, D imports C, et
    # cetera, while modules X and Y and Z are not part of the chain.

    def test_stability_when_nothing_is_wrong(self):
        events = [
            ('A', 'A'),
            ('B', 'B'),
            ('C', 'C'),
            ('D', 'D'),
            ('E', 'E'),
            ]
        self.assertEqual(improve_order(events), ['A', 'B', 'C', 'D', 'E'])

    def test_simple_swap(self):
        events = [
            ('A', 'A'),
            ('B', 'B'),
            ('D', 'CD'),
            ('C', ''),
            ('E', 'E'),
            ]
        self.assertEqual(improve_order(events), ['A', 'B', 'C', 'D', 'E'])

    def test_importing_main_module_first(self):
        events = [
            ('E', 'ABCDE'),
            ('A', ''),
            ('B', ''),
            ('C', ''),
            ('D', ''),
            ]
        self.assertEqual(improve_order(events), ['A', 'B', 'C', 'D', 'E'])

    def test_importing_middle_module_first(self):
        events = [
            ('C', 'ABC'),
            ('A', ''),
            ('B', ''),
            ('D', 'D'),
            ('E', 'E'),
            ]
        self.assertEqual(improve_order(events), ['A', 'B', 'C', 'D', 'E'])

    def test_having_two_module_swaps(self):
        events = [
            ('A', 'A'),
            ('C', 'BC'),
            ('B', ''),
            ('E', 'DE'),
            ('D', ''),
            ]
        self.assertEqual(improve_order(events), ['A', 'B', 'C', 'D', 'E'])

    def test_which_module_moves(self):
        # If module D is moved to the end of the list, then does D
        # simply get moved back, or does E get moved to its right?
        events = [
            ('A', 'A'),
            ('B', 'B'),
            ('C', 'C'),
            ('E', 'DE'),
            ('X', 'X'),
            ('Y', 'Y'),
            ('Z', 'Z'),
            ('D', ''),
            ]
        self.assertEqual(improve_order(events),
                         ['A', 'B', 'C', 'X', 'Y', 'Z', 'D', 'E'])

    def test_learning_about_new_modules(self):
        events = [
            ('A', 'A'),
            ('B', 'BX'),
            ('C', 'C'),
            ('D', 'DYZ'),
            ('E', 'E'),
            ]
        self.assertEqual(improve_order(events),
                         ['A', 'X', 'B', 'C', 'Z', 'Y', 'D', 'E'])

if __name__ == '__main__':
    unittest.main()
