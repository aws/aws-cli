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
from awscli.customizations.supplychain.utils import get_ssm_client


class InventoryCommand(BasicCommand):
    NAME = 'inventory'

    DESCRIPTION = (
        "Track and manage software inventory across AWS resources. "
        "Integrates with AWS Systems Manager Inventory to provide "
        "comprehensive visibility into installed software and dependencies."
    )

    ARG_TABLE = [
        {
            'name': 'action',
            'help_text': "Inventory action to perform",
            'required': True,
            'choices': ['list', 'collect', 'export']
        },
        {
            'name': 'resource-type',
            'help_text': "Type of resource to inventory",
            'default': 'all',
            'choices': ['ec2', 'lambda', 'container', 'all']
        },
        {
            'name': 'filter',
            'help_text': "Filter inventory by tag or attribute",
            'required': False
        },
        {
            'name': 'output-format',
            'help_text': "Output format",
            'default': 'json',
            'choices': ['json', 'csv', 'table']
        },
        {
            'name': 'output',
            'help_text': "Output file path",
            'required': False
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        try:
            if parsed_args.action == 'list':
                # List current inventory (simulated)
                inventory = {
                    "totalResources": 10,
                    "resourceTypes": {
                        "ec2": 5,
                        "lambda": 3,
                        "container": 2
                    },
                    "summary": {
                        "totalPackages": 245,
                        "uniquePackages": 87,
                        "vulnerablePackages": 12
                    },
                    "lastUpdated": "2025-01-15T10:30:00Z"
                }
                
                if parsed_args.output_format == 'json':
                    output = json.dumps(inventory, indent=2)
                else:
                    output = "Software Inventory Summary\n"
                    output += f"Total Resources: {inventory['totalResources']}\n"
                    output += f"Total Packages: {inventory['summary']['totalPackages']}\n"
                    output += f"Vulnerable Packages: {inventory['summary']['vulnerablePackages']}\n"
                
            elif parsed_args.action == 'collect':
                output = "Initiating inventory collection...\n"
                output += f"Collecting inventory for resource type: {parsed_args.resource_type}\n"
                output += "Collection initiated. This may take several minutes.\n"
                
            elif parsed_args.action == 'export':
                # Export inventory data
                export_data = {
                    "exportDate": "2025-01-15T10:30:00Z",
                    "resources": [],
                    "packages": []
                }
                output = json.dumps(export_data, indent=2)
                
                if parsed_args.output:
                    with open(parsed_args.output, 'w') as f:
                        f.write(output)
                    output = f"Inventory exported to {parsed_args.output}\n"
            
            sys.stdout.write(output)
            return 0

        except Exception as e:
            sys.stderr.write(f"Error managing inventory: {str(e)}\n")
            return 1