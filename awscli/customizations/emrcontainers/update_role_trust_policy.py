# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import json
import logging

from awscli.customizations.commands import BasicCommand
from awscli.customizations.emrcontainers.constants \
    import TRUST_POLICY_STATEMENT_FORMAT, \
    TRUST_POLICY_STATEMENT_ALREADY_EXISTS, \
    TRUST_POLICY_UPDATE_SUCCESSFUL
from awscli.customizations.emrcontainers.base36 import Base36
from awscli.customizations.emrcontainers.eks import EKS
from awscli.customizations.emrcontainers.iam import IAM
from awscli.customizations.utils import uni_print

LOG = logging.getLogger(__name__)


# Method to parse the arguments to get the region value
def get_region(session, parsed_globals):
    region = parsed_globals.region

    if region is None:
        region = session.get_config_variable('region')

    return region


def check_if_statement_exists(expected_statement, actual_assume_role_document):
    if actual_assume_role_document is None:
        return False

    existing_statements = actual_assume_role_document.get("Statement", [])
    for existing_statement in existing_statements:
        matches = check_if_dict_matches(expected_statement, existing_statement)
        if matches:
            return True

    return False


def check_if_dict_matches(expected_dict, actual_dict):
    if len(expected_dict) != len(actual_dict):
        return False

    for key in expected_dict:
        key_str = str(key)
        val = expected_dict[key_str]
        if isinstance(val, dict):
            if not check_if_dict_matches(val, actual_dict.get(key_str, {})):
                return False
        else:
            if key_str not in actual_dict or actual_dict[key_str] != str(val):
                return False

    return True


class UpdateRoleTrustPolicyCommand(BasicCommand):
    NAME = 'update-role-trust-policy'

    DESCRIPTION = BasicCommand.FROM_FILE(
        'emr-containers',
        'update-role-trust-policy',
        '_description.rst'
    )

    ARG_TABLE = [
        {
            'name': 'cluster-name',
            'help_text': ("Specify the name of the Amazon EKS cluster with "
                          "which the IAM Role would be used."),
            'required': True
        },
        {
            'name': 'namespace',
            'help_text': ("Specify the namespace from the Amazon EKS cluster "
                          "with which the IAM Role would be used."),
            'required': True
        },
        {
            'name': 'role-name',
            'help_text': ("Specify the IAM Role name that you want to use"
                          "with Amazon EMR on EKS."),
            'required': True
        },
        {
            'name': 'iam-endpoint',
            'no_paramfile': True,
            'help_text': ("The  IAM  endpoint  to call for updating the role "
                          "trust policy. This is optional and should only be"
                          "specified when a custom endpoint should be called"
                          "for IAM operations."),
            'required': False
        },
        {
            'name': 'dry-run',
            'action': 'store_true',
            'default': False,
            'help_text': ("Print the merged trust policy document to"
                          "stdout instead of updating the role trust"
                          "policy directly."),
            'required': False
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        """Call to run the commands"""

        self._cluster_name = parsed_args.cluster_name
        self._namespace = parsed_args.namespace
        self._role_name = parsed_args.role_name
        self._region = get_region(self._session, parsed_globals)
        self._endpoint_url = parsed_args.iam_endpoint
        self._dry_run = parsed_args.dry_run

        result = self._update_role_trust_policy(parsed_globals)
        uni_print(result)
        uni_print("\n")

        return 0

    def _update_role_trust_policy(self, parsed_globals):
        """Method to update  trust policy if not done already"""

        base36 = Base36()

        eks_client = EKS(self._session.create_client(
            'eks',
            region_name=self._region,
            verify=parsed_globals.verify_ssl
        ))

        account_id = eks_client.get_account_id(self._cluster_name)
        oidc_provider = eks_client.get_oidc_issuer_id(self._cluster_name)

        base36_encoded_role_name = base36.encode(self._role_name)
        LOG.debug('Base36 encoded role name: %s', base36_encoded_role_name)
        trust_policy_statement = json.loads(TRUST_POLICY_STATEMENT_FORMAT %
            {
                "AWS_ACCOUNT_ID": account_id,
                "OIDC_PROVIDER": oidc_provider,
                "NAMESPACE": self._namespace,
                "BASE36_ENCODED_ROLE_NAME": base36_encoded_role_name
            }
        )

        LOG.debug('Computed Trust Policy Statement:\n%s', json.dumps(
            trust_policy_statement, indent=2))
        iam_client = IAM(self._session.create_client(
            'iam',
            region_name=self._region,
            endpoint_url=self._endpoint_url,
            verify=parsed_globals.verify_ssl
        ))

        assume_role_document = iam_client.get_assume_role_policy(
            self._role_name)
        matches = check_if_statement_exists(trust_policy_statement,
                                            assume_role_document)

        if not matches:
            LOG.debug('Role %s does not have the required trust policy ',
                      self._role_name)

            existing_statements = assume_role_document.get("Statement")
            if existing_statements is None:
                assume_role_document["Statement"] = [trust_policy_statement]
            else:
                existing_statements.append(trust_policy_statement)

            if self._dry_run:
                return json.dumps(assume_role_document, indent=2)
            else:
                LOG.debug('Updating trust policy of role %s', self._role_name)
                iam_client.update_assume_role_policy(self._role_name,
                                                     assume_role_document)
                return TRUST_POLICY_UPDATE_SUCCESSFUL % self._role_name
        else:
            return TRUST_POLICY_STATEMENT_ALREADY_EXISTS % self._role_name
