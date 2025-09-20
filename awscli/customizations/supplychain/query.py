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


class QueryCommand(BasicCommand):
    NAME = 'query'

    DESCRIPTION = (
        "Query supply chain data across AWS services. Search for packages, "
        "vulnerabilities, SBOMs, and attestations across your infrastructure."
    )

    ARG_TABLE = [
        {
            'name': 'type',
            'help_text': "The type of data to query",
            'required': True,
            'choices': ['package', 'vulnerability', 'sbom', 'attestation', 'all']
        },
        {
            'name': 'query-string',
            'help_text': "The search query string",
            'required': False
        },
        {
            'name': 'package',
            'help_text': "Filter by package name",
            'required': False
        },
        {
            'name': 'severity',
            'help_text': "Filter vulnerabilities by severity",
            'required': False
        },
        {
            'name': 'limit',
            'help_text': "Maximum number of results to return",
            'default': 100,
            'cli_type_name': 'integer'
        },
        {
            'name': 'output-format',
            'help_text': "Output format",
            'default': 'json',
            'choices': ['json', 'table']
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        try:
            # Simulated query results
            results = {
                "queryType": parsed_args.type,
                "totalResults": 0,
                "results": []
            }

            # Add sample results based on query type
            if parsed_args.type == 'vulnerability':
                results['results'] = [
                    {
                        "cveId": "CVE-2024-1234",
                        "severity": "HIGH",
                        "package": "example-package",
                        "version": "1.0.0",
                        "affectedResources": ["arn:aws:ecr:us-east-1:123456789012:repository/app"]
                    }
                ]
                results['totalResults'] = len(results['results'])

            elif parsed_args.type == 'package':
                results['results'] = [
                    {
                        "packageName": "example-package",
                        "version": "1.0.0",
                        "locations": ["arn:aws:lambda:us-east-1:123456789012:function:my-function"],
                        "vulnerabilities": 0
                    }
                ]
                results['totalResults'] = len(results['results'])

            # Output results
            if parsed_args.output_format == 'json':
                sys.stdout.write(json.dumps(results, indent=2))
                sys.stdout.write("\n")
            else:
                sys.stdout.write(f"Query type: {parsed_args.type}\n")
                sys.stdout.write(f"Total results: {results['totalResults']}\n")
                if results['results']:
                    sys.stdout.write("\nResults:\n")
                    for i, result in enumerate(results['results'], 1):
                        sys.stdout.write(f"  {i}. {json.dumps(result)}\n")

            return 0

        except Exception as e:
            sys.stderr.write(f"Error executing query: {str(e)}\n")
            return 1