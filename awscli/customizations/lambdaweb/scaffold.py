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
import os
import textwrap

from awscli.customizations.lambdaweb import constants, naming
from awscli.customizations.lambdaweb.exceptions import InvalidSourceError

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


def _intro(function_name, docs, trailer):
    return textwrap.fill(
        f'`{function_name}` is an AWS Lambda Web Function, '
        f'{docs.project_summary}. {trailer}',
        width=79,
        break_long_words=False,
        break_on_hyphens=False,
    )


def _deploy_block(function_name, docs):
    command = _deploy_command(function_name)
    if docs.deploy_alias:
        return f'{docs.deploy_alias}\n# or\n{command}'
    return command


def _readme(function_name, runtime):
    docs = runtime.docs
    runtime_port = constants.RUNTIME_HTTP_PORT
    local_url = f'http://localhost:{runtime_port}'
    intro = _intro(
        function_name,
        docs,
        'This project was scaffolded with `aws lambda-web deploy`.',
    )
    return f"""\
# {function_name}

{intro}

## Why Lambda Web Functions

{docs.why_bullet}
- Each execution environment can serve concurrent requests.
- Lambda scales the Web Function with traffic, including to zero when idle.
- Deploy across multiple AWS Regions behind one endpoint. Lambda routes each
  request to the Region with the lowest latency for the caller.
- Stream responses as your application produces them.

## Run locally

```bash
{docs.start_command}
```

Open [{local_url}]({local_url}) in a browser, or run:

```bash
curl {local_url}
```

To change the response, edit `{docs.entry_file}` and restart.

## Deploy

```bash
{_deploy_block(function_name, docs)}
```

Run `aws lambda-web deploy help` for all deployment options.

The command uploads the source code, deploys a revision, updates the endpoint,
and prints the endpoint URL.

## How it works

{docs.how_it_works}

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


def _agents_md(function_name, runtime):
    docs = runtime.docs
    runtime_port = constants.RUNTIME_HTTP_PORT
    confirm_create_flag = constants.CONFIRM_CREATE_FLAG
    log_group = naming.log_group_name(function_name)
    commands = f'{docs.start_command:<16} # run locally on port {runtime_port}'
    if docs.deploy_alias:
        commands += f'\n{docs.deploy_alias:<16} # deploy a new revision'
    intro = _intro(
        function_name, docs, 'Deploy it with `aws lambda-web deploy`.'
    )
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

{intro}

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

{docs.runtime_contract}

## Layout

{docs.layout}

## Dependencies

{docs.dependencies}

## How `deploy` packages the code

These rules apply to `aws lambda-web deploy`, not to the service. Another
deployment path, such as uploading a `.zip` file to Amazon S3, determines its
own package contents.

{docs.packaging}

## Creating resources

Creating a Web Function or endpoint requires confirmation. Use
`{confirm_create_flag}` to confirm without a prompt. In an interactive terminal,
pressing Enter at the prompt provides the same confirmation.

## Commands

```bash
{commands}

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


def write_hello_world(source_dir, function_name, runtime):
    """Write the runtime's starter into *source_dir* and return its entry.

    The path must not exist or must identify an existing empty directory.
    Raises ``InvalidSourceError`` instead of overwriting existing content.
    Returns the entry in the runtime's display form.
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
    files = dict(runtime.scaffold_files(function_name))
    files['README.md'] = _readme(function_name, runtime)
    files['AGENTS.md'] = _agents_md(function_name, runtime)
    try:
        os.makedirs(source_dir, exist_ok=True)
        for relpath, content in files.items():
            _write(os.path.join(source_dir, relpath), content)
    except OSError as e:
        detail = e.strerror or str(e)
        raise InvalidSourceError(
            f"Unable to create the starter application in '{source_dir}': "
            f'{detail}. The directory might contain files created before the '
            'error.'
        ) from e
    return runtime.scaffold_entry()


def _write(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
