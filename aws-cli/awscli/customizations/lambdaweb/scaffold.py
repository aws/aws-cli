# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import json
import os

from awscli.customizations.lambdaweb import constants, naming
from awscli.customizations.lambdaweb.exceptions import InvalidSourceError

SCAFFOLD_ENTRY = 'server.ts'
_AGENT_TOOLKIT_REGION = 'us-east-1'
_AGENT_TOOLKIT_MIN_CLI_VERSION = '2.35.9'
_LAMBDA_WEB_SKILL = 'aws-lambda-web-functions'
_LAMBDA_WEB_DOCS_URL = (
    'https://docs.aws.amazon.com/lambda/latest/dg/web-functions.html'
)
_AGENT_SETUP_GUIDE_URL = (
    'https://docs.aws.amazon.com/lambda/latest/dg/agent-setup-guide.html'
)


def _deploy_base_command(function_name):
    return f'aws lambda-web deploy --name {function_name}'


def _deploy_command(function_name):
    return f'{_deploy_base_command(function_name)} --code .'


def _server_ts():
    runtime_port = constants.RUNTIME_HTTP_PORT
    local_port_env_var = constants.LOCAL_PORT_ENV_VAR
    return f"""\
// Minimal AWS Lambda Web Function HTTP server.
//
// You can replace this with any code or framework that starts an HTTP server.
import http from 'node:http';

// Lambda sends requests to port {runtime_port}. Set {local_port_env_var} for local development.
const port = Number(process.env.{local_port_env_var} ?? {runtime_port});

const server = http.createServer((req, res) => {{
  res.writeHead(200, {{ 'content-type': 'application/json' }});
  res.end(JSON.stringify({{ message: 'Hello from Lambda Web!', path: req.url }}));
}});

server.listen(port, () => {{
  console.log(`listening on port ${{port}}`);
}});
"""


def _package_json(function_name):
    obj = {
        "name": function_name,
        "version": "1.0.0",
        "private": True,
        "type": "module",
        "main": SCAFFOLD_ENTRY,
        "scripts": {
            "start": f"node {SCAFFOLD_ENTRY}",
            "deploy": _deploy_command(function_name),
        },
    }
    return json.dumps(obj, indent=2) + '\n'


def _readme(function_name):
    runtime_port = constants.RUNTIME_HTTP_PORT
    local_url = f'http://localhost:{runtime_port}'
    return f"""\
# {function_name}

`{function_name}` is an AWS Lambda Web Function, a Node.js HTTP server that
AWS Lambda runs behind an HTTPS endpoint. This project was scaffolded with
`aws lambda-web deploy`.

## Why Lambda Web Functions

- Deploy a standard Node.js application that listens on a port without
  Lambda-specific adapters, wrappers, or handler changes.
- Each execution environment can serve concurrent requests.
- Lambda scales the Web Function with traffic, including to zero when idle.
- Deploy across multiple AWS Regions behind one endpoint. Lambda routes each
  request to the Region with the lowest latency for the caller.
- Stream responses as your application produces them.

## Run locally

```bash
npm start
```

Open [{local_url}]({local_url}) in a browser, or run:

```bash
curl {local_url}
```

To change the response, edit `server.ts` and restart.

## Deploy

```bash
npm run deploy
# or
{_deploy_command(function_name)}
```

Run `aws lambda-web deploy help` for all deployment options.

The command uploads the source code, deploys a revision, updates the endpoint,
and prints the endpoint URL.

## How it works

`server.ts` is a Node.js HTTP server that listens on port {runtime_port}.
There is no handler to export and no adapter to install. AWS Lambda starts it
and forwards HTTPS requests to it. Frameworks such as Express, Fastify, Hono,
and Next.js use the same HTTP server model.

Each deployment uploads the directory as a new revision and updates the
endpoint. The first deployment creates the Web Function and endpoint and can
create an execution role and deployment bucket.

## Set up an AI coding agent

To configure Claude Code, Cursor, Kiro, Codex, or another AI coding agent with
the AWS MCP Server and AWS skills, run:

```bash
aws configure agent-toolkit --region {_AGENT_TOOLKIT_REGION}
```

This command requires AWS CLI version {_AGENT_TOOLKIT_MIN_CLI_VERSION} or later.
The Agent Toolkit API is available only in `{_AGENT_TOOLKIT_REGION}`.

## Learn more

- [Lambda Web Functions]({_LAMBDA_WEB_DOCS_URL})
  for concepts, endpoints, scaling, and monitoring
- [`AGENTS.md`](./AGENTS.md)
  for context for AI coding agents
- [Agent setup guide]({_AGENT_SETUP_GUIDE_URL})
  for per-agent setup steps and Lambda skills
"""


def _agents_md(function_name):
    runtime_port = constants.RUNTIME_HTTP_PORT
    local_port_env_var = constants.LOCAL_PORT_ENV_VAR
    runtime_architecture = constants.RUNTIME_ARCHITECTURE
    runtime = constants.DEFAULT_RUNTIME
    entry_file = constants.RUNTIME_ENTRY_FILE
    entry_env_var = constants.ENTRYPOINT_ENV_VAR
    confirm_create_flag = constants.CONFIRM_CREATE_FLAG
    log_group = naming.log_group_name(function_name)
    return f"""\
# AGENTS.md

Context for AI coding agents working on this AWS Lambda Web Function. For setup
and deployment, see [`README.md`](./README.md).

## Skills

The `{_LAMBDA_WEB_SKILL}` skill covers this service in more depth than this
file. Load it before nontrivial changes, and prefer it to assumptions from
other Lambda function types. To check whether the skill is installed and add
it if needed, run:

```bash
aws agent-toolkit list-installed-skills
aws configure agent-toolkit --yes --region {_AGENT_TOOLKIT_REGION}
aws agent-toolkit add-skill \\
    --skill-name {_LAMBDA_WEB_SKILL} \\
    --region {_AGENT_TOOLKIT_REGION}
```

`aws configure agent-toolkit --yes` configures detected AI coding agents with
the AWS MCP Server and default AWS skills. These commands require AWS CLI
version {_AGENT_TOOLKIT_MIN_CLI_VERSION} or later.

The Agent Toolkit API is available only in `{_AGENT_TOOLKIT_REGION}`. Use
`--region {_AGENT_TOOLKIT_REGION}` unless that AWS Region is already configured.

## Project

`{function_name}` is an AWS Lambda Web Function, a Node.js HTTP server that AWS
Lambda runs behind an HTTPS endpoint. Deploy it with `aws lambda-web deploy`.

Web Functions use their own API and HTTP server programming model. They are not
a setting on handler-based Lambda functions, which the documentation calls
Lambda Event Functions. This project has no exported handler, `event` or
`context` argument, Amazon API Gateway API, Lambda Function URL, or adapter
library. Read per-request context from the HTTP request headers. Lambda adds
`lambda-web-request-id` and `lambda-web-endpoint-name`. The `x-forwarded-for`
header contains the caller address.

Before you make structural changes, confirm the behavior in the linked
documentation or in the `{_LAMBDA_WEB_SKILL}` skill.

Do not convert this project to an exported handler, and do not manage it with
AWS SAM, AWS CDK, or `aws lambda` commands. If the workspace also contains
Lambda Event Functions, confirm which function to change before editing.

## Runtime contract

- Serve HTTP on port {runtime_port}. Lambda sends every request there.
  `{local_port_env_var}` changes the port for local runs only. Do not set it
  with `--env`.
- Keep the `server.listen(...)` call or the framework equivalent, such as
  `app.listen(...)`. A server on another port can still report `Active`, but
  requests return HTTP 502 responses.
- Responses stream as the application writes them. Use `res.write(...)` or pipe
  a stream to the response, and end the response when complete. There is no
  `streamifyResponse` wrapper to add.

## Layout

- `server.ts`: The entry point and HTTP server. If you rename it, update `main`
  in `package.json`.
- `package.json`: ES module configuration and the `start` and `deploy` scripts.
- The runtime is `{runtime}` and runs this TypeScript directly. There is no
  build step. Node.js strips types instead of compiling them.
  Transpile TypeScript features that require code generation, such as
  enums, namespaces, and parameter properties, and point `main` to the output.

## Dependencies

- Web Functions use the `{runtime_architecture}` architecture. The architecture
  is not configurable. Dependencies with native binaries need an
  `{runtime_architecture}` version.
- After adding dependencies, consider bundling the application to keep the
  deployment package small. Uploading `node_modules` as-is also works without a
  build step.
- Keep secrets out of the source tree. Pass nonsecret configuration with
  `--env`.

## How `deploy` packages the code

These rules apply to `aws lambda-web deploy`, not to the service. Another
deployment path, such as uploading a `.zip` file to Amazon S3, determines its
own package contents.

- `deploy` packages the `--code` directory. It does not run `npm install`,
  bundle, or compile the application, so install dependencies first.
- Hidden files and directories are excluded by default, except for known
  framework build paths. Use `--include-hidden-files` when the application
  needs another hidden path. Exact excluded files, such as `.env` or `*.pem`,
  require `--force-include`. Excluded directories, such as `.ssh`, remain
  excluded.
- Symlinks are skipped instead of followed. With pnpm or a workspace, install
  a layout of real files by using `npm install` or pnpm with
  `node-linker=hoisted`.
- The runtime loads `{entry_file}` by default and does not read `package.json`.
  For a different entry file, `deploy` adds an `{entry_file}` wrapper that
  imports the file. To load the file directly without a wrapper, set
  `{entry_env_var}` with `--env`.
  Use a path relative to the package root. Do not use that environment variable
  with `--entry-point`.

## Creating resources

Creating a Web Function or endpoint requires confirmation. Use
`{confirm_create_flag}` to confirm without a prompt. In an interactive terminal,
pressing Enter at the prompt provides the same confirmation.

## Commands

```bash
npm start        # run locally on port {runtime_port}
npm run deploy   # deploy a new revision

aws lambda-web deploy help          # show all deploy options
aws lambda-web list-web-functions   # list Web Functions
```

The first invocation creates the `{log_group}` log group. To follow its logs,
run:

```bash
aws logs tail {log_group} --follow
```

Common deploys:

```bash
# Deploy the latest code
{_deploy_command(function_name)}

# Update an environment variable without uploading code
{_deploy_base_command(function_name)} --env MY_SETTING=value

# Add a staging endpoint and reuse the deployed code
{_deploy_base_command(function_name)} \\
    --endpoint-name staging {confirm_create_flag}
```

## Learn more

- [Lambda Web Functions]({_LAMBDA_WEB_DOCS_URL})
  for concepts, runtimes, endpoints, scaling, and monitoring
"""


def is_empty_dir(path):
    """Return True if *path* does not exist or is an empty directory."""
    try:
        if not os.path.exists(path):
            return True
        return os.path.isdir(path) and not os.listdir(path)
    except OSError as e:
        detail = e.strerror or str(e)
        raise InvalidSourceError(
            f"Unable to inspect --code directory '{path}': {detail}."
        ) from e


def write_hello_world(source_dir, function_name):
    """Write the hello-world starter into *source_dir* and return the entry.

    The path must not exist or must identify an existing empty directory.
    Raises ``InvalidSourceError`` instead of overwriting existing content.
    Returns the entry path relative to *source_dir*.
    """
    if os.path.exists(source_dir) and not os.path.isdir(source_dir):
        raise InvalidSourceError(
            '--hello-world requires a --code path that does not exist or '
            f"identifies an existing empty directory, but '{source_dir}' is "
            'a file.'
        )
    if not is_empty_dir(source_dir):
        raise InvalidSourceError(
            '--hello-world requires a --code path that does not exist or '
            f"identifies an existing empty directory, but '{source_dir}' "
            'contains files. The command does not overwrite files. Specify a '
            'different --code directory, or remove '
            '--hello-world to deploy the existing code.'
        )
    try:
        os.makedirs(source_dir, exist_ok=True)
        _write(os.path.join(source_dir, SCAFFOLD_ENTRY), _server_ts())
        _write(
            os.path.join(source_dir, 'package.json'),
            _package_json(function_name),
        )
        _write(os.path.join(source_dir, 'README.md'), _readme(function_name))
        _write(
            os.path.join(source_dir, 'AGENTS.md'), _agents_md(function_name)
        )
    except OSError as e:
        detail = e.strerror or str(e)
        raise InvalidSourceError(
            f"Unable to create the starter application in '{source_dir}': "
            f'{detail}. The directory might contain files created before the '
            'error.'
        ) from e
    return SCAFFOLD_ENTRY


def _write(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
