"""Tests for whole-function mutation support in function_trampoline_arrangement.

These tests surface the bug where mutations targeting the FunctionDef itself
(as produced by the LLM operator) are silently dropped because deep_replace
cannot find the original_node by identity after .with_changes().

Kept in a separate file to isolate from upstream test_mutation.py and
minimize merge conflicts when rebasing the submodule.
"""

import libcst as cst

from mutmut.file_mutation import (
    Mutation,
    function_trampoline_arrangement,
    mutate_file_contents,
)
from mutmut.plugin_manager import get_plugin_manager


def test_whole_function_mutation_applied():
    """Mutations targeting the FunctionDef itself must produce mutant functions
    with the mutated body, not copies of the original.

    This is the pattern used by the LLM operator: original_node IS the
    FunctionDef, and mutated_node is a freshly parsed FunctionDef with
    a different body.
    """
    source = "def foo():\n    return 1\n"
    module = cst.parse_module(source)
    original_func = module.body[0]
    assert isinstance(original_func, cst.FunctionDef)

    mutated_source = "def foo():\n    return 2\n"
    mutated_func = cst.parse_module(mutated_source).body[0]
    assert isinstance(mutated_func, cst.FunctionDef)

    mutation = Mutation(
        original_node=original_func,
        mutated_node=mutated_func,
        contained_by_top_level_function=original_func,
    )

    nodes, mutant_names, _ = function_trampoline_arrangement(
        original_func, [mutation], class_name=None
    )

    assert len(mutant_names) == 1

    mutant_funcs = [
        n for n in nodes if isinstance(n, cst.FunctionDef) and "_1" in n.name.value
    ]
    assert len(mutant_funcs) == 1

    mutant_code = cst.parse_module("").code_for_node(mutant_funcs[0])

    assert "return 2" in mutant_code, (
        f"Whole-function mutation was not applied. Mutant body:\n{mutant_code}"
    )
    assert "return 1" not in mutant_code


def test_subnode_mutation_still_works():
    """Standard sub-node mutations (interior nodes like BinaryOp) must
    continue to work correctly — regression guard for the fix."""
    source = "def foo(a, b):\n    return a + b\n"
    module = cst.parse_module(source)
    original_func = module.body[0]
    assert isinstance(original_func, cst.FunctionDef)

    class FindAdd(cst.CSTVisitor):
        def __init__(self):
            self.add_node = None

        def visit_Add(self, node):
            self.add_node = node

    finder = FindAdd()
    original_func.visit(finder)
    assert finder.add_node is not None

    mutation = Mutation(
        original_node=finder.add_node,
        mutated_node=cst.Subtract(),
        contained_by_top_level_function=original_func,
    )

    nodes, mutant_names, _ = function_trampoline_arrangement(
        original_func, [mutation], class_name=None
    )

    assert len(mutant_names) == 1

    mutant_funcs = [
        n for n in nodes if isinstance(n, cst.FunctionDef) and "_1" in n.name.value
    ]
    assert len(mutant_funcs) == 1

    mutant_code = cst.parse_module("").code_for_node(mutant_funcs[0])
    assert "a - b" in mutant_code, f"Sub-node mutation not applied:\n{mutant_code}"
    assert "a + b" not in mutant_code


def test_multiple_whole_function_mutations():
    """Multiple whole-function mutations on the same function must each produce
    a distinct mutant with the correct body and sequential naming (_1, _2, _3)."""
    source = "def foo(x):\n    return x\n"
    module = cst.parse_module(source)
    original_func = module.body[0]
    assert isinstance(original_func, cst.FunctionDef)

    variants = ["def foo(x):\n    return x + 1\n", "def foo(x):\n    return -x\n"]
    mutations = [
        Mutation(
            original_node=original_func,
            mutated_node=cst.parse_module(src).body[0],
            contained_by_top_level_function=original_func,
        )
        for src in variants
    ]

    nodes, mutant_names, _ = function_trampoline_arrangement(
        original_func, mutations, class_name=None
    )

    assert len(mutant_names) == 2
    assert "_1" in mutant_names[0]
    assert "_2" in mutant_names[1]

    code = cst.parse_module("")
    mutant_bodies = {
        n.name.value: code.code_for_node(n)
        for n in nodes
        if isinstance(n, cst.FunctionDef) and "__mutmut_" in n.name.value
    }
    mutant_1 = next(v for k, v in mutant_bodies.items() if k.endswith("_1"))
    mutant_2 = next(v for k, v in mutant_bodies.items() if k.endswith("_2"))

    assert "x + 1" in mutant_1, f"Mutant _1 wrong body:\n{mutant_1}"
    assert "-x" in mutant_2, f"Mutant _2 wrong body:\n{mutant_2}"


def test_mixed_subnode_and_whole_function_mutations():
    """A function with both sub-node mutations (Add->Sub) and whole-function
    mutations must produce correct output for both types in a single
    function_trampoline_arrangement call."""
    source = "def calc(a, b):\n    return a + b\n"
    module = cst.parse_module(source)
    original_func = module.body[0]
    assert isinstance(original_func, cst.FunctionDef)

    # Sub-node mutation: Add -> Subtract
    class FindAdd(cst.CSTVisitor):
        def __init__(self):
            self.add_node = None

        def visit_Add(self, node):
            self.add_node = node

    finder = FindAdd()
    original_func.visit(finder)
    assert finder.add_node is not None

    subnode_mutation = Mutation(
        original_node=finder.add_node,
        mutated_node=cst.Subtract(),
        contained_by_top_level_function=original_func,
    )

    # Whole-function mutation: completely different body
    whole_func_source = "def calc(a, b):\n    return a * b\n"
    whole_mutation = Mutation(
        original_node=original_func,
        mutated_node=cst.parse_module(whole_func_source).body[0],
        contained_by_top_level_function=original_func,
    )

    # Pass both types interleaved: sub-node first, whole-function second
    nodes, mutant_names, _ = function_trampoline_arrangement(
        original_func, [subnode_mutation, whole_mutation], class_name=None
    )

    assert len(mutant_names) == 2

    code = cst.parse_module("")
    mutant_bodies = {
        n.name.value: code.code_for_node(n)
        for n in nodes
        if isinstance(n, cst.FunctionDef) and "__mutmut_" in n.name.value
    }
    mutant_1 = next(v for k, v in mutant_bodies.items() if k.endswith("_1"))
    mutant_2 = next(v for k, v in mutant_bodies.items() if k.endswith("_2"))

    # _1 is sub-node: Add replaced with Subtract
    assert "a - b" in mutant_1, f"Sub-node mutant _1 wrong:\n{mutant_1}"
    assert "a + b" not in mutant_1

    # _2 is whole-function: body replaced with a * b
    assert "a * b" in mutant_2, f"Whole-function mutant _2 wrong:\n{mutant_2}"
    assert "a + b" not in mutant_2


def test_mutate_file_contents_with_functiondef_operator(monkeypatch):
    """End-to-end: register a FunctionDef operator (like mutmut-llm does)
    and verify the generated mutant file contains the mutated function body."""

    source = "def greet(name):\n    return 'hello ' + name\n"
    mutated_source_str = "def greet(name):\n    return 'goodbye ' + name\n"

    def operator_replace_hello(node: cst.FunctionDef):
        mutated = cst.parse_module(mutated_source_str).body[0]
        yield mutated

    original_hook = get_plugin_manager().hook.mutmut_register_operators

    def mock_register_operators():
        results = original_hook()
        results.append([(cst.FunctionDef, operator_replace_hello)])
        return results

    monkeypatch.setattr(
        get_plugin_manager().hook,
        "mutmut_register_operators",
        mock_register_operators,
    )

    mutated_code, mutant_names = mutate_file_contents("test.py", source)

    assert len(mutant_names) >= 1
    assert "goodbye" in mutated_code, (
        f"FunctionDef operator mutation not in output:\n{mutated_code}"
    )
