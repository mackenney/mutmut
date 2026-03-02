import pluggy

hookspec = pluggy.HookspecMarker("mutmut")
hookimpl = pluggy.HookimplMarker("mutmut")


class MutmutHookSpec:
    @hookspec
    def mutmut_configure(self, config):
        """Modify config after loading from pyproject.toml."""

    @hookspec
    def mutmut_register_operators(self):
        """Return additional mutation operators.
        Each operator: (cst_node_type, callable).
        Returns: list of (type, callable) tuples.
        All results flattened and appended to built-in operators.
        """

    @hookspec
    def mutmut_register_commands(self, cli_group):
        """Register additional click commands on the mutmut CLI group."""

    @hookspec
    def mutmut_filter_mutations(self, filename, mutations):
        """Filter or augment mutations after generation for a file."""

    @hookspec
    def mutmut_mutations_created(self, filename, source_by_mutant_name):
        """Called after mutations are created for a file.
        source_by_mutant_name: dict mapping mutant name to source ('builtin' or 'llm')."""

    @hookspec
    def mutmut_pre_test(self, mutant_name, tests):
        """Called before testing a mutant (before fork)."""

    @hookspec
    def mutmut_post_test(self, mutant_name, exit_code, status, duration):
        """Called after a mutant test completes."""

    @hookspec
    def mutmut_post_run(self, stats, source_file_mutation_data):
        """Called after all mutation testing completes."""

    @hookspec(firstresult=True)
    def mutmut_select_tests(self, mutant_name, default_tests):
        """Override test selection for a mutant.
        firstresult=True: first non-None wins.
        """

    @hookspec(firstresult=True)
    def mutmut_skip_node(self, node):
        """Decide whether to skip mutating a CST node.
        Returns: True to skip, None to defer to built-in rules.
        firstresult=True: first True wins.
        """
