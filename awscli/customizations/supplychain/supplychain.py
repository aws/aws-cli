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

from awscli.customizations.commands import BasicCommand
from awscli.customizations.supplychain.sbom import GenerateSBOMCommand
from awscli.customizations.supplychain.scan import ScanCommand
from awscli.customizations.supplychain.attest import AttestCommand
from awscli.customizations.supplychain.query import QueryCommand
from awscli.customizations.supplychain.policy import PolicyCommand
from awscli.customizations.supplychain.inventory import InventoryCommand
from awscli.customizations.supplychain.report import ReportCommand


class SupplyChainCommand(BasicCommand):
    NAME = 'supplychain'

    DESCRIPTION = (
        "AWS Supply Chain Security commands provide comprehensive software "
        "supply chain security and management capabilities. These commands "
        "help organizations secure their software supply chains, meet "
        "regulatory requirements, prevent supply chain attacks, and provide "
        "visibility into software composition across AWS services."
    )

    SYNOPSIS = 'aws supplychain <subcommand> [options]'

    EXAMPLES = (
        'Generate an SBOM for a container image::\n'
        '\n'
        '    $ aws supplychain generate-sbom --image-uri 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:latest --format spdx\n'
        '\n'
        'Scan a Lambda function for vulnerabilities::\n'
        '\n'
        '    $ aws supplychain scan --resource-arn arn:aws:lambda:us-east-1:123456789012:function:my-function --severity CRITICAL,HIGH\n'
        '\n'
        'Create an attestation for a container image::\n'
        '\n'
        '    $ aws supplychain attest --resource-arn arn:aws:ecr:us-east-1:123456789012:repository/my-app --predicate-type slsa-provenance\n'
        '\n'
        'Query for vulnerable packages::\n'
        '\n'
        '    $ aws supplychain query --type vulnerability --severity CRITICAL --package log4j\n'
    )

    SUBCOMMANDS = [
        {'name': 'generate-sbom', 'command_class': GenerateSBOMCommand},
        {'name': 'scan', 'command_class': ScanCommand},
        {'name': 'attest', 'command_class': AttestCommand},
        {'name': 'query', 'command_class': QueryCommand},
        {'name': 'policy', 'command_class': PolicyCommand},
        {'name': 'inventory', 'command_class': InventoryCommand},
        {'name': 'report', 'command_class': ReportCommand},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        # This is only called when 'aws supplychain' is run without subcommands
        # In this case, we'll show the help
        self._display_help(parsed_args, parsed_globals)
        return 1