import json
import logging
import re
import shlex
from contextlib import redirect_stdout

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp.server import Context

from awscli.clidriver import create_clidriver
from awscli.compat import StringIO
from awscli.help import PosixHelpRenderer

LOG = logging.getLogger(__name__)


def get_aws_cli_mcp_server(*, port: str, host: str) -> FastMCP:
    mcp_server = FastMCP(
        name="AWS CLI MCP server",
        instructions="MCP server to execute AWS CLI commands",
        port=int(port),
        host=host,
    )
    mcp_server.add_tool(run_aws_cli)
    return mcp_server


_CONTROL_SEQUENCE = re.compile("\x1b\\[\\d+m")


def _remove_control_sequence(content: str):
    return _CONTROL_SEQUENCE.sub("", content)


def _patch_aws_cli_pager(buf: StringIO):
    def patched_send_output_to_pager(self, output):
        content = output.decode('utf-8')
        buf.write(_remove_control_sequence(content) + "\n")
        buf.flush()
        return

    PosixHelpRenderer._send_output_to_pager = patched_send_output_to_pager


def run_aws_cli(ctx: Context, aws_cli: str) -> dict:
    """Run the aws cli command and return the JSON response."""
    tokens = shlex.split(aws_cli)
    if set(tokens) & set(("|", ">", ">>", "||", "&&", "&")):
        raise ToolError(
            "run_aws_cli cannot handle pipelines. You can only run one AWS CLI command at one time."
        )

    sub_command = tokens[1:]
    LOG.debug(f"Running AWS CLI command {sub_command!r}")
    try:
        output = StringIO()
        _patch_aws_cli_pager(output)
        with redirect_stdout(output):
            clidriver = create_clidriver(sub_command)
            return_code = clidriver.main(sub_command)
            try:
                parsed_json = json.load(output)
                return parsed_json
            except json.JSONDecodeError:
                return {"output": output.getvalue()}

    except SystemExit as sys_exit:
        if sys_exit.code != 0:
            raise ToolError("Non 0 return code from aws cli")
        else:
            raise ToolError(f"Unknown error occured when executing {aws_cli}")

    except BaseException as e:
        raise ToolError(str(e))
