
import unittest
from .importation import partially_order

class AssayTests(unittest.TestCase):

    # We assume A imports B, that imports C, that imports D, et cetera.

    def test_stability_when_nothing_is_wrong(self):
        order = ['E', 'D', 'C', 'B', 'A']
        edges = {}
        self.assertEqual(partially_order(order, edges),
                         ['E', 'D', 'C', 'B', 'A'])

    def test_simple_swap(self):
        order = ['E', 'D', 'B', 'C', 'A']
        edges = {'B': 'C'}
        self.assertEqual(partially_order(order, edges),
                         ['E', 'D', 'C', 'B', 'A'])

    def test_importing_main_module_first(self):
        order = ['A', 'B', 'C', 'D', 'E']
        edges = {'A': 'BCDE'}
        self.assertEqual(partially_order(order, edges),
                         ['B', 'C', 'D', 'E', 'A'])

    def test_importing_middle_module_first(self):
        order = ['C', 'D', 'E', 'B', 'A']
        edges = {'C': 'DE'}
        self.assertEqual(partially_order(order, edges),
                         ['D', 'E', 'C', 'B', 'A'])


if __name__ == '__main__':
    unittest.main()
