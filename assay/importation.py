"""Routines that understand Python importation."""

from collections import defaultdict
from importlib import import_module

def get_directory_of(name):
    """Return the base directory of a package, or None for a plain module."""
    module = import_module(name)
    return getattr(module, '__path__', None)

def partially_order(existing_order, edges):
    existing_nodes = set(existing_order)
    key = {node: i for i, node in enumerate(existing_order)}.get
    visited = set()
    new_order = []

    edges2 = defaultdict(set)
    for a, blist in edges.items():
        for b in blist:
            edges2[b].add(a)

    def visit(node):
        if node in visited:
            return
        visited.add(node)
        children = edges2.get(node, None)
        if children is not None:
            for child in sorted(children, key=key):
                visit(child)
        new_order.append(node)
        for node2 in sorted(edges.get(node, ())):
            if node2 not in existing_nodes:
                new_order.append(node2)

    for node in reversed(existing_order):
        visit(node)

    new_order.reverse()
    return new_order
