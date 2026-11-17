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


SERVICE_NAME = 'lambda-web'

CONFIRM_CREATE_ARG = 'create'
CONFIRM_CREATE_FLAG = f'--{CONFIRM_CREATE_ARG}'

# The CLI pins a runtime only when a new function omits --runtime. Update this
# value when the recommended default runtime changes. Function updates inherit
# the deployed runtime unless the customer specifies --runtime.
DEFAULT_RUNTIME = 'nodejs24.x'
RUNTIME_HTTP_PORT = 3000
LOCAL_PORT_ENV_VAR = 'LOCAL_PORT'
RUNTIME_ARCHITECTURE = 'arm64'
DEFAULT_ENDPOINT_TYPE = 'HomeRegion'
DEFAULT_AUTH_TYPE = 'ApplicationManaged'
DEFAULT_AUTO_DEPLOYMENT_MODE = 'LatestRevision'
DEFAULT_ENDPOINT_NAME = 'dev'

# Endpoint types that require caller-supplied AWS Regions.
REGION_REQUIRED_ENDPOINT_TYPES = ('MultiRegion', 'PerRegion')

# ``autoDeploymentMode`` value that marks the auto-deploying endpoint.
AUTO_DEPLOY_LATEST_REVISION = 'LatestRevision'

# The only autoDeploymentMode the service accepts for MultiRegion/PerRegion
# endpoint types; HomeRegion endpoints have no such constraint.
DISABLED_AUTO_DEPLOYMENT_MODE = 'Disabled'

S3_BUCKET_NAMESPACE = 'account-regional'

LOG_GROUP_PREFIX = '/aws/lambda/web'

# Partition-specific console domains.
CONSOLE_DOMAIN_BY_PARTITION = {
    'aws': 'console.aws.amazon.com',
    'aws-cn': 'console.amazonaws.cn',
    'aws-us-gov': 'console.amazonaws-us-gov.com',
}
CONSOLE_HOST_PATH = '/lambda/home'
CONSOLE_WEB_FUNCTION_FRAGMENT = '#/web-functions/'

DEFAULT_POLL_INTERVAL_SECONDS = 5
DEFAULT_ACTIVATION_TIMEOUT_SECONDS = 600
IAM_PROPAGATION_RETRIES = 6
IAM_PROPAGATION_RETRY_SLEEP_SECONDS = 5

# Separate from SDK retries because each conflict retry refreshes endpoint
# state before rebuilding the request.
ENDPOINT_UPDATE_CONFLICT_RETRIES = 4
ENDPOINT_UPDATE_CONFLICT_SLEEP_SECONDS = 3

# Upper bound on exponential backoff between throttled activation polls.
THROTTLE_BACKOFF_CAP_SECONDS = 60

S3_MULTIPART_THRESHOLD_BYTES = 8 * 1024 * 1024
# The service rejects bundles over this size, so deploy fails fast
# client-side instead of uploading a bundle that cannot deploy.
BUNDLE_SIZE_MAX_BYTES = 512 * 1024 * 1024

# Service principal used in both the role trust policy and S3 bucket policy.
WEB_FUNCTION_SERVICE_PRINCIPAL = 'lambda.amazonaws.com'

FUNCTION_NAME_PATTERN = r'^(?![-_])[a-zA-Z0-9_-]{2,64}(?<![-_])\Z'

RUNTIME_ENTRY_FILE = 'index.js'

# The runtime reads this env var to override the entry file. The CLI does not
# set it itself but honors a customer-set value (skips the wrapper). Rejected
# as a user-supplied ``--env`` key alongside ``--entry-point`` (ambiguous).
ENTRYPOINT_ENV_VAR = 'AWS_LAMBDA_NODEJS_ENTRYPOINT'

ENTRY_POINT_CANDIDATES = (
    'index.js',
    'index.mjs',
    'index.cjs',
    'server.js',
    'server.mjs',
    'server.cjs',
    'dist/index.js',
    'dist/server.js',
    'build/index.js',
    'build/server.js',
)

# Hidden build and runtime paths included without --include-hidden-files.
DEFAULT_INCLUDED_HIDDEN_DIRECTORIES = (
    '.next',
    '.nuxt',
    '.svelte-kit',
    '.output',
    '.prisma',
    '.yarn',
)

DEFAULT_INCLUDED_HIDDEN_FILES = (
    '.pnp.cjs',
    '.pnp.data.json',
    '.pnp.loader.mjs',
    '.pnp.js',
)

# Patterns excluded from deployment bundles
DEFAULT_EXCLUDE_PATTERNS = (
    '.git/',
    '.svn/',
    '.hg/',
    '__pycache__/',
    'node_modules/.cache/',
    '.aws-sam/',
    '.terraform/',
    '.aws/',
    '.ssh/',
    '.DS_Store',
    '*.pyc',
    '*.pem',
    '*.key',
    'id_rsa*',
    '.env',
    '.env.*',
    '.npmrc',
    '.netrc',
)
