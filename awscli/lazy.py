import importlib

from awscli.commands import CLICommand


class LazyCommand(CLICommand):
    """A command-table entry that defers importing its real implementation.

    Sits in the command table like any other CLICommand, but only imports
    the actual module (and creates the real command object) when the command
    is invoked or its help is accessed.
    """

    def __init__(self, name, session, module_path, class_name):
        self._name = name
        self._session = session
        self._module_path = module_path
        self._class_name = class_name
        self._real = None
        self._lineage = [self]

    def _resolve(self):
        if self._real is None:
            mod = importlib.import_module(self._module_path)
            cls = getattr(mod, self._class_name)
            self._real = cls(self._session)
            self._real.lineage = self._lineage
        return self._real

    def __call__(self, args, parsed_globals):
        return self._resolve()(args, parsed_globals)

    def create_help_command(self):
        return self._resolve().create_help_command()

    @property
    def arg_table(self):
        return self._resolve().arg_table

    @property
    def subcommand_table(self):
        return self._resolve().subcommand_table

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def lineage(self):
        return self._lineage

    @lineage.setter
    def lineage(self, value):
        self._lineage = value
        if self._real is not None:
            self._real.lineage = value
