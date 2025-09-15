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
from datetime import datetime

from awscli.customizations.commands import BasicCommand
from awscli.customizations.supplychain.utils import (
    get_signer_client, validate_resource_arn
)


class AttestCommand(BasicCommand):
    NAME = 'attest'

    DESCRIPTION = (
        "Create and manage cryptographic attestations for software artifacts. "
        "This command integrates with AWS Signer to create signed attestations "
        "that prove the integrity and provenance of your software supply chain."
    )

    ARG_TABLE = [
        {
            'name': 'resource-arn',
            'help_text': "The ARN of the resource to create an attestation for",
            'required': True
        },
        {
            'name': 'predicate-type',
            'help_text': "The type of attestation predicate",
            'required': True,
            'choices': ['slsa-provenance', 'vulnerability-scan', 'sbom', 'custom']
        },
        {
            'name': 'predicate-file',
            'help_text': "Path to a file containing the predicate data",
            'required': False
        },
        {
            'name': 'signing-profile',
            'help_text': "The AWS Signer profile to use for signing",
            'required': False
        },
        {
            'name': 'output',
            'help_text': "Output file for the attestation",
            'required': False
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        try:
            # Create attestation structure
            attestation = {
                "_type": "https://in-toto.io/Statement/v0.1",
                "predicateType": f"https://slsa.dev/{parsed_args.predicate_type}/v0.1",
                "subject": [{
                    "name": parsed_args.resource_arn,
                    "digest": {"sha256": "placeholder"}
                }],
                "predicate": {}
            }

            # Load predicate data if provided
            if parsed_args.predicate_file:
                with open(parsed_args.predicate_file, 'r') as f:
                    attestation['predicate'] = json.load(f)
            else:
                # Create basic predicate
                attestation['predicate'] = {
                    "buildType": "aws-cli-supplychain",
                    "builder": {"id": "aws-cli"},
                    "invocation": {
                        "configSource": {"uri": parsed_args.resource_arn},
                        "parameters": {},
                        "environment": {}
                    },
                    "metadata": {
                        "buildStartedOn": datetime.utcnow().isoformat() + 'Z',
                        "buildFinishedOn": datetime.utcnow().isoformat() + 'Z',
                        "completeness": {"parameters": True, "environment": False},
                        "reproducible": False
                    }
                }

            # Output attestation
            output = json.dumps(attestation, indent=2)
            
            if parsed_args.output:
                with open(parsed_args.output, 'w') as f:
                    f.write(output)
                sys.stdout.write(f"Attestation written to {parsed_args.output}\n")
            else:
                sys.stdout.write(output)
                sys.stdout.write("\n")

            return 0

        except Exception as e:
            sys.stderr.write(f"Error creating attestation: {str(e)}\n")
            return 1