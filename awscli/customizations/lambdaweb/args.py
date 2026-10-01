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
from awscli.customizations.lambdaweb import constants

_EXCLUDED_PATTERNS_HELP = ', '.join(
    f'``{pattern}``' for pattern in constants.DEFAULT_EXCLUDE_PATTERNS
)
_INCLUDED_HIDDEN_PATHS_HELP = ', '.join(
    [
        f'``{directory}/``'
        for directory in constants.DEFAULT_INCLUDED_HIDDEN_DIRECTORIES
    ]
    + [
        f'``{filename}``'
        for filename in constants.DEFAULT_INCLUDED_HIDDEN_FILES
    ]
)

DESCRIPTION = (
    'Deploys a local HTTP server to an AWS Lambda Web Function. The command '
    'creates a Web Function or deploys a new revision to an existing Web '
    'Function, applies the requested endpoint configuration, and returns the '
    'endpoint URL.\n\n'
    'The ``deploy`` command coordinates API operations for common create and '
    'update workflows. For configuration that is not available through '
    '``deploy``, such as weighted revision routing or connecting a Web '
    'Function to a VPC, use the ``aws lambda-web`` commands for specific '
    'API operations.\n'
)


ARG_TABLE = [
    {
        'name': 'name',
        'required': True,
        'help_text': (
            'Name of the Web Function. The name must be between 2 and 64 '
            'characters long. It can contain letters, numbers, hyphens (-), '
            'and underscores (_). It cannot start or end with a hyphen or '
            'underscore.'
        ),
    },
    {
        'name': 'code',
        # not required here: it defaults to ``./<name>`` with
        # --hello-world, and omitting it reuses the deployed code.
        'help_text': (
            'Path to the directory that contains the Web Function source code. '
            'This option is required when you create a Web Function unless you '
            'use ``--hello-world``. For an existing Web Function, omit this '
            'option to update configuration and reuse the deployed code. With '
            '``--hello-world``, the default is ``./&lt;name&gt;``.'
        ),
    },
    {
        'name': 'hello-world',
        'action': 'store_true',
        'default': False,
        'help_text': (
            'Create and deploy a minimal TypeScript starter that '
            f'listens on port ``{constants.RUNTIME_HTTP_PORT}``. Set '
            f'``{constants.LOCAL_PORT_ENV_VAR}`` to use a different port for '
            'local development. The starter uses '
            f'``{constants.DEFAULT_RUNTIME}``. Only ``--name`` is required.'
        ),
    },
    {
        'name': constants.CONFIRM_CREATE_ARG,
        'action': 'store_true',
        'default': False,
        'help_text': (
            'Confirm creation of a Web Function or endpoint without a prompt. '
            'If you omit this option in an interactive terminal, the command '
            'prompts for confirmation. In a non-interactive environment, you '
            'must specify this option when creation is required.'
        ),
    },
    {
        'name': 'runtime',
        'help_text': (
            'Runtime identifier for the Web Function. When you create a Web '
            'Function, the default is '
            f'``{constants.DEFAULT_RUNTIME}``. When you update a Web Function, '
            'the command reuses its current runtime.'
        ),
    },
    {
        'name': 'entry-point',
        'help_text': (
            'Path to the entry file, relative to ``--code``. The entry file '
            'must start the HTTP server. If you omit this option, the command '
            'checks the ``main`` and ``exports`` fields in ``package.json``, '
            'then checks common files such as ``index.js`` and ``server.js``. '
            'If the entry file is not ``index.js``, the command adds an '
            '``index.js`` wrapper that imports it. To have the runtime load a '
            f'file directly, set ``{constants.ENTRYPOINT_ENV_VAR}`` with '
            '``--env`` '
            'instead. Do not use ``--entry-point`` and '
            f'``{constants.ENTRYPOINT_ENV_VAR}`` together.'
        ),
    },
    {
        'name': 'execution-role-arn',
        'help_text': (
            'Amazon Resource Name (ARN) of an AWS Identity and Access '
            'Management (AWS IAM) execution role. When you create a Web '
            'Function and omit this option, the command creates a role named '
            '``awscli-lambdaweb-&lt;name&gt;``. When you update a Web Function '
            'and omit this option, the command reuses its current role.'
        ),
    },
    {
        'name': 'bucket-name',
        'help_text': (
            'Name of an existing Amazon Simple Storage Service (Amazon S3) '
            'bucket for the deployment package. If you omit this option, the '
            'command uses a managed bucket named '
            '``awscli-lambdaweb-&lt;account-id&gt;-&lt;region&gt;-an``.'
        ),
    },
    {
        'name': 'env',
        'action': 'append',
        'default': None,
        'help_text': (
            'Environment variable in ``KEY=VALUE`` format. To specify '
            'multiple variables, repeat this option for each variable. For '
            'example, ``--env KEY1=VALUE1 --env KEY2=VALUE2``. For an existing '
            'Web Function, the command adds or replaces the specified keys and '
            'preserves other variables. To remove a variable, use '
            '``--unset-env``. To select the file that the runtime loads, set '
            f'``{constants.ENTRYPOINT_ENV_VAR}`` with this option. Do not use '
            f'``{constants.ENTRYPOINT_ENV_VAR}`` with ``--entry-point``.'
        ),
    },
    {
        'name': 'unset-env',
        'action': 'append',
        'default': None,
        'help_text': (
            'Name of an environment variable to remove from an existing '
            'Web Function. You can specify this option multiple times. The '
            'command applies this option after ``--env``, so removal takes '
            'precedence when you specify the same key with both options. This '
            'option has no effect when you create a Web Function.'
        ),
    },
    {
        'name': 'timeout-seconds',
        'cli_type_name': 'integer',
        'help_text': (
            'Maximum amount of time, in seconds, that the Web Function can '
            'run. When you update a Web Function and omit this option, the '
            'command reuses its current timeout.'
        ),
    },
    {
        'name': 'max-concurrency-per-environment',
        'cli_type_name': 'integer',
        'help_text': (
            'Maximum number of concurrent requests that each execution '
            'environment can process. When you update a Web Function and omit '
            'this option, the command reuses its current value.'
        ),
    },
    {
        'name': 'kms-key-arn',
        'help_text': (
            'ARN of the AWS Key Management Service (AWS KMS) key that '
            "encrypts the Web Function revision's code and environment "
            "variables. This key doesn't encrypt the deployment package in "
            'Amazon S3. When you update a Web Function and omit this option, '
            'the command reuses its current AWS KMS key.'
        ),
    },
    # Choices are loaded from ApplicationLogLevel at runtime.
    {
        'name': 'application-log-level',
        'help_text': (
            'Minimum log level for application logs. When you update a '
            'Web Function and omit this option, the command reuses its '
            'current application log level.'
        ),
    },
    # Choices are loaded from SystemLogLevel at runtime.
    {
        'name': 'system-log-level',
        'help_text': (
            'Minimum log level for system logs. When you update a Web Function '
            'and omit this option, the command reuses its current system log '
            'level.'
        ),
    },
    {
        'name': 'revision-description',
        'help_text': 'Description for the revision.',
    },
    {
        'name': 'include-hidden-files',
        'action': 'store_true',
        'default': False,
        'help_text': (
            'Include hidden files and directories in the deployment package. '
            'The command includes these build and runtime paths even when you '
            f'omit this option: {_INCLUDED_HIDDEN_PATHS_HELP}. The command '
            'still excludes entries that match these patterns: '
            f'{_EXCLUDED_PATTERNS_HELP}. You can use ``--force-include`` to '
            'include an exact file, but it does not override directory '
            'exclusions.'
        ),
    },
    {
        'name': 'force-include',
        'action': 'append',
        'default': None,
        'help_text': (
            'Path to a regular file, relative to ``--code``, to include when '
            'the command would otherwise exclude it. To include multiple '
            'files, repeat this option. To include a file from a hidden '
            'directory, also use ``--include-hidden-files``. This option '
            'cannot include symlinks or files inside an excluded directory. '
            'Verify that each file does not contain credentials or other '
            'secrets. Use AWS Secrets Manager for runtime secrets.'
        ),
    },
    {
        'name': 'no-wait',
        'action': 'store_true',
        'default': False,
        'help_text': (
            'Return without waiting for endpoint activation. When you create '
            'a Web Function, the initial endpoint is included in the request. '
            'When you update a Web Function and request an endpoint change, '
            'the command waits for the revision to become ``Active``, submits '
            'the endpoint change, and then returns.'
        ),
    },
    {
        'name': 'activation-timeout',
        'cli_type_name': 'integer',
        'default': constants.DEFAULT_ACTIVATION_TIMEOUT_SECONDS,
        'help_text': (
            'Maximum time, in seconds, to wait for activation. Default: '
            f'{constants.DEFAULT_ACTIVATION_TIMEOUT_SECONDS}.'
        ),
    },
    {
        'name': 'progress-frequency',
        'cli_type_name': 'integer',
        'help_text': (
            'Interval, in seconds, between progress messages while the '
            'command waits for activation. Default: '
            f'{constants.DEFAULT_POLL_INTERVAL_SECONDS}.'
        ),
    },
    {
        'name': 'endpoint-name',
        'help_text': (
            'Name of the endpoint to deploy. When you create a Web Function, '
            f'the default is ``{constants.DEFAULT_ENDPOINT_NAME}``. For an '
            'existing Web Function, the command updates the named endpoint or '
            'creates it after confirmation.'
        ),
    },
    # Choices are loaded from EndpointType at runtime.
    {
        'name': 'endpoint-type',
        'help_text': (
            'Type of endpoint to create. When you create an endpoint and omit '
            'this option, the command uses '
            f'``{constants.DEFAULT_ENDPOINT_TYPE}``. After you create an '
            'endpoint, you cannot change its type. You can create another '
            'endpoint with a different type.'
        ),
    },
    # Choices are loaded from AuthType at runtime.
    {
        'name': 'auth-type',
        'help_text': (
            'Authorization type for the endpoint. When you create an endpoint '
            'and omit this option, the command uses '
            f'``{constants.DEFAULT_AUTH_TYPE}``. When you update an endpoint '
            'and omit this option, the command preserves its current '
            'authorization type.'
        ),
    },
    # Choices are loaded from AutoDeploymentMode at runtime.
    {
        'name': 'auto-deployment-mode',
        'help_text': (
            'Automatic deployment mode for the endpoint. The default for a '
            '``HomeRegion`` endpoint is '
            f'``{constants.DEFAULT_AUTO_DEPLOYMENT_MODE}``. ``MultiRegion`` '
            'and ``PerRegion`` endpoints use '
            f'``{constants.DISABLED_AUTO_DEPLOYMENT_MODE}``. '
            '``LatestRevision`` serves the newest revision. ``Disabled`` '
            'serves the configured revision weights. For an existing endpoint, '
            'omit this option to preserve its current mode.'
        ),
    },
    {
        'name': 'regions',
        'help_text': (
            'Comma-separated list of AWS Region codes for a ``MultiRegion`` or '
            '``PerRegion`` endpoint. For example, '
            '``--endpoint-type MultiRegion --regions '
            'us-east-1,us-west-2``. Include at least one AWS Region other than '
            'the home Region. For a ``HomeRegion`` endpoint, omit this option '
            'or specify only the home Region. The ``--region`` option or your '
            'AWS CLI configuration determines the home Region where the CLI '
            'sends the deploy request. You cannot change the AWS Regions after '
            'the endpoint is created.'
        ),
    },
    {
        'name': 'tags',
        'action': 'append',
        'default': None,
        'help_text': (
            'Tag in ``KEY=VALUE`` format to apply to the Web Function. To '
            'specify multiple tags, repeat this option for each tag. For '
            'example, ``--tags KEY1=VALUE1 --tags KEY2=VALUE2``. When you '
            'update a Web Function, the command adds or replaces the specified '
            'tags and preserves tags with other keys. To remove tags, use '
            '``aws lambda-web untag-resource`` with the Web Function ARN and '
            '``--tag-keys``.'
        ),
    },
    {
        'name': 'max-environments',
        'cli_type_name': 'integer',
        'help_text': (
            'Maximum number of concurrent execution environments for the '
            'endpoint. When you update an existing endpoint, omit this option '
            'to preserve its current value.'
        ),
    },
    # Supported rate limits can vary by account or AWS Region. The CLI checks
    # only the model's minimum value and lets the Lambda Web API validate the
    # supported increments.
    {
        'name': 'rate-limit',
        'cli_type_name': 'integer',
        'help_text': (
            'Maximum number of requests per second for the endpoint. The '
            'supported values and effective limit can vary by AWS account or '
            'AWS Region. When you update an existing endpoint, omit this '
            'option to preserve its current value.'
        ),
    },
    {
        'name': 'description',
        'help_text': (
            'Description for the endpoint. For an existing endpoint, the '
            'command updates the description when this value differs from the '
            'current description.'
        ),
    },
]


# repeatable args: argparse collects a list, but ``CustomArgument`` builds a
# scalar model, so ``_build_arg_table`` nulls it to skip scalar validation.
APPEND_ARGS = ('env', 'force-include', 'tags', 'unset-env')


INT_ARG_VALIDATION = {
    'timeout_seconds': (
        '--timeout-seconds',
        'ServiceConfigTimeoutSecondsInteger',
    ),
    'max_concurrency_per_environment': (
        '--max-concurrency-per-environment',
        'ServiceConfigMaxConcurrencyPerEnvironmentInteger',
    ),
    'max_environments': (
        '--max-environments',
        'ScalingConfigMaxEnvironmentsInteger',
    ),
    'rate_limit': ('--rate-limit', 'ThrottleConfigRateLimitInteger'),
}


# endpoint-shape args the service treats as immutable once the endpoint
# exists; they are not members of ``UpdateWebFunctionEndpointRequest``.
ENDPOINT_IMMUTABLE_ARGS = (
    ('endpoint_type', '--endpoint-type'),
    ('regions', '--regions'),
)

# endpoint-shape args that only apply while an endpoint is being created.
ENDPOINT_CREATE_ARGS = (
    ('endpoint_type', '--endpoint-type'),
    ('auth_type', '--auth-type'),
    ('auto_deployment_mode', '--auto-deployment-mode'),
    ('regions', '--regions'),
    ('description', '--description'),
    ('max_environments', '--max-environments'),
    ('rate_limit', '--rate-limit'),
)
