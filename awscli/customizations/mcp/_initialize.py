from ._mcp_command import Mcp


def awscli_initialize(cli):
    """The entry point to the AWS CLI MCP server."""
    cli.register('building-command-table.main', add_mcp_command)


def add_mcp_command(command_table, session, **kwargs):
    command_table['mcp-server'] = Mcp(session)
