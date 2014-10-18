import unittest
from .importation import partially_order

class AssayTests(unittest.TestCase):

    # We assume that module B imports A, C imports B, D imports C, et
    # cetera, while modules X and Y and Z are not part of the chain.

    def test_stability_when_nothing_is_wrong(self):
        order = ['A', 'B', 'C', 'D', 'E']
        edges = {}
        self.assertEqual(partially_order(order, edges),
                         ['A', 'B', 'C', 'D', 'E'])

    def test_simple_swap(self):
        order = ['A', 'B', 'D', 'C', 'E']
        edges = {'D': 'C'}
        self.assertEqual(partially_order(order, edges),
                         ['A', 'B', 'C', 'D', 'E'])

    def test_importing_main_module_first(self):
        order = ['E', 'D', 'C', 'B', 'A']
        edges = {'E': 'ABCD'}
        self.assertEqual(partially_order(order, edges),
                         ['D', 'C', 'B', 'A', 'E'])

    def test_importing_middle_module_first(self):
        order = ['C', 'B', 'A', 'D', 'E']
        edges = {'C': 'BA'}
        self.assertEqual(partially_order(order, edges),
                         ['B', 'A', 'C', 'D', 'E'])

    def test_having_two_module_swaps(self):
        order = ['A', 'C', 'B', 'E', 'D']
        edges = {'C': 'B', 'E': 'D'}
        self.assertEqual(partially_order(order, edges),
                         ['A', 'B', 'C', 'D', 'E'])

    def test_which_module_moves(self):
        # If module C is moved to the end of the list, then does C
        # simply get moved back, or does D get moved to its right?
        order = ['A', 'B', 'D', 'X', 'Y', 'Z', 'C']
        edges = {'D': 'C'}
        self.assertEqual(partially_order(order, edges),
                         ['A', 'B', 'C', 'D', 'X', 'Y', 'Z'])

if __name__ == '__main__':
    unittest.main()
