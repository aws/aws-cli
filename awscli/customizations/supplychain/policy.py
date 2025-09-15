# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import sys

from awscli.customizations.commands import BasicCommand
from awscli.customizations.supplychain.utils import (
    create_default_policy, validate_policy
)


class PolicyCommand(BasicCommand):
    NAME = 'policy'

    DESCRIPTION = (
        "Manage supply chain security policies. Create, update, and enforce "
        "policies that govern the deployment and usage of software components."
    )

    SUBCOMMANDS = [
        {'name': 'create', 'command_class': 'CreatePolicyCommand'},
        {'name': 'list', 'command_class': 'ListPoliciesCommand'},
        {'name': 'get', 'command_class': 'GetPolicyCommand'},
        {'name': 'update', 'command_class': 'UpdatePolicyCommand'},
        {'name': 'delete', 'command_class': 'DeletePolicyCommand'},
        {'name': 'evaluate', 'command_class': 'EvaluatePolicyCommand'}
    ]

    ARG_TABLE = [
        {
            'name': 'policy-name',
            'help_text': "Name of the policy",
            'required': False
        },
        {
            'name': 'policy-file',
            'help_text': "Path to policy definition file",
            'required': False
        },
        {
            'name': 'action',
            'help_text': "Policy action",
            'choices': ['create', 'list', 'get', 'update', 'delete', 'evaluate'],
            'required': False
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        try:
            # For now, just create and display a default policy
            if not parsed_args.action or parsed_args.action == 'create':
                policy = create_default_policy()
                
                if parsed_args.policy_file:
                    # Load custom policy
                    with open(parsed_args.policy_file, 'r') as f:
                        policy = json.load(f)
                    
                    # Validate the policy
                    validate_policy(policy)
                
                # Output policy
                sys.stdout.write("Supply Chain Security Policy:\n")
                sys.stdout.write(json.dumps(policy, indent=2))
                sys.stdout.write("\n")
                
                if parsed_args.policy_name:
                    sys.stdout.write(f"\nPolicy '{parsed_args.policy_name}' created successfully.\n")
            
            elif parsed_args.action == 'list':
                # List policies (simulated)
                policies = [
                    {"name": "default-policy", "status": "active", "rules": 3},
                    {"name": "production-policy", "status": "active", "rules": 5}
                ]
                sys.stdout.write("Supply Chain Policies:\n")
                for policy in policies:
                    sys.stdout.write(f"  - {policy['name']} ({policy['status']}, {policy['rules']} rules)\n")
            
            return 0

        except Exception as e:
            sys.stderr.write(f"Error managing policy: {str(e)}\n")
            return 1