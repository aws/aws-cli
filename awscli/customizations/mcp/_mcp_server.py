import json
import logging
import shlex
import sys
from contextlib import redirect_stdout

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp.server import Context
from pydantic import BaseModel

from awscli.clidriver import create_clidriver
from awscli.compat import StringIO

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
