import logging

from awscli.customizations.commands import BasicCommand

from ._mcp_server import get_aws_cli_mcp_server

LOG = logging.getLogger(__name__)


class StartCommand(BasicCommand):
    NAME = "start"
    DESCRIPTION = "Start the AWS CLI MCP server."
    USAGE = "aws mcp-server start"
    ARG_TABLE = [
        {
            "name": "transport",
            "nargs": "?",
            "choices": ["stdio", "streamable-http"],
            "default": "stdio",
            'positional_arg': False,
            'help_text': "Specify the transport to run the JSON-RPC server used by MCP. (default: stdio)",
        },
        {
            "name": "port",
            "nargs": "?",
            "default": "8080",
            'positional_arg': False,
            'help_text': "Specify the port that the MCP server listens to if protocol is streamable-http",
        },
        {
            "name": "host",
            "nargs": "?",
            "default": "127.0.0.1",
            'positional_arg': False,
            'help_text': "Specify the host that the MCP server listens to if protocol is streamable-http",
        },
    ]

    def _run_main(self, parsed_args, parsed_globals):
        mcp_server = get_aws_cli_mcp_server(
            port=parsed_args.port,
            host=parsed_args.host,
        )
        mcp_server.run(transport=parsed_args.transport)
