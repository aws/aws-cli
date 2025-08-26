from typing import override

from awscli.customizations.commands import BasicCommand

from ._mcp_subcommands import StartCommand


class Mcp(BasicCommand):
    NAME = "mcp-server"
    DESCRIPTION = "Use AWS CPI as a MCP server"
    SYNOPSIS = "aws mcp <Command> [<Arg> ...]"
    SUBCOMMANDS = [{'name': 'start', 'command_class': StartCommand}]

    @override
    def _run_main(self, parsed_args, parsed_globals):
        if parsed_args.subcommand is None:
            self._raise_usage_error()
