"""Routines that understand Python importation."""

from importlib import import_module

def get_directory_of(name):
    """Return the base directory of a package, or None for a plain module."""
    module = import_module(name)
    return getattr(module, '__path__', None)

def partially_order(existing_order, edges):
    key = {node: i for i, node in enumerate(existing_order)}.get
    visited = set()
    new_order = []

    def visit(node):
        if node in visited:
            return
        visited.add(node)
        children = edges.get(node, None)
        if children is not None:
            for child in sorted(children, key=key):
                visit(child)
        new_order.append(node)

    for node in existing_order:
        visit(node)
    #new_order.reverse()
    return new_order
