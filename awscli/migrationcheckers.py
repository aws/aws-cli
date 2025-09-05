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

class MigrationCheckerResult:
    def __init__(self, triggered, warning_message):
        self.triggered = triggered
        self.warning_message = warning_message


FILE_PREFIX_PARAMS_WARNING = "For input parameters of type blob, behavior when using the file:// prefix changed in AWS CLI v2. See https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-binaryparam."
WEB_LINK_PARAM_WARNING = "For input parameters that have a prefix of http:// or https://, AWS CLI v2 will no longer automatically request the content of the URL for the parameter, and the cli_follow_urlparam option has been removed. See https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-paramfile."
PAGER_DEFAULT_WARNING = "By default, AWS CLI v2 returns all output through your operating system’s default pager program. See https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-output-pager."
ECR_GET_LOGIN_WARNING = "The ecr get-login command has been removed in AWS CLI v2. See https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-ecr-get-login."
HIDDEN_ALIAS_WARNING = "You have entered a command argument that uses at least 1 of 21 hidden aliases that were removed in AWS CLI v2. See https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-aliases."

MIGRATION_CHECKERS = {
    'file_prefix_param': MigrationCheckerResult(False, FILE_PREFIX_PARAMS_WARNING),
    'web_link_param': MigrationCheckerResult(False, WEB_LINK_PARAM_WARNING),
    'pager_default': MigrationCheckerResult(False, PAGER_DEFAULT_WARNING),
    'ecr_get_login': MigrationCheckerResult(False, ECR_GET_LOGIN_WARNING),
    'hidden_alias': MigrationCheckerResult(False, HIDDEN_ALIAS_WARNING),
}
