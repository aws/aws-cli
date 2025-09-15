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
import time

from awscli.customizations.commands import BasicCommand
from awscli.customizations.supplychain.utils import (
    get_inspector_client, get_ecr_client,
    validate_resource_arn, parse_severity_filter,
    format_scan_results
)
from awscli.customizations.supplychain.exceptions import ScanError


class ScanCommand(BasicCommand):
    NAME = 'scan'

    DESCRIPTION = (
        "Scan AWS resources for vulnerabilities and security issues. "
        "This command integrates with Amazon Inspector to perform "
        "comprehensive vulnerability scanning on container images, "
        "Lambda functions, EC2 instances, and other supported resources."
    )

    ARG_TABLE = [
        {
            'name': 'resource-arn',
            'help_text': (
                "The ARN of the resource to scan. This can be an ECR repository, "
                "Lambda function, EC2 instance, or other supported AWS resource."
            ),
            'required': False
        },
        {
            'name': 'image-uri',
            'help_text': (
                "The URI of a container image in ECR to scan. "
                "Format: <registry>/<repository>:<tag>"
            ),
            'required': False
        },
        {
            'name': 'severity',
            'help_text': (
                "Filter results by severity level. Comma-separated list of: "
                "CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL"
            ),
            'default': 'CRITICAL,HIGH,MEDIUM'
        },
        {
            'name': 'output-format',
            'help_text': "Output format for scan results",
            'default': 'table',
            'choices': ['table', 'json']
        },
        {
            'name': 'wait',
            'action': 'store_true',
            'help_text': (
                "Wait for the scan to complete before returning results. "
                "By default, the command initiates a scan and returns immediately."
            )
        },
        {
            'name': 'max-wait-time',
            'help_text': (
                "Maximum time in seconds to wait for scan completion (default: 300)"
            ),
            'default': 300,
            'cli_type_name': 'integer'
        },
        {
            'name': 'package-filter',
            'help_text': (
                "Filter results to only show vulnerabilities for specific packages"
            ),
            'required': False
        },
        {
            'name': 'cve-filter',
            'help_text': (
                "Filter results to only show specific CVE IDs (comma-separated)"
            ),
            'required': False
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        # Validate that either resource-arn or image-uri is provided
        if not parsed_args.resource_arn and not parsed_args.image_uri:
            sys.stderr.write(
                "Error: Either --resource-arn or --image-uri must be specified\n"
            )
            return 1

        try:
            # Parse severity filter
            severity_filter = parse_severity_filter(parsed_args.severity)

            if parsed_args.image_uri:
                findings = self._scan_container_image(
                    parsed_args, parsed_globals, severity_filter
                )
            else:
                findings = self._scan_resource(
                    parsed_args, parsed_globals, severity_filter
                )

            # Apply additional filters if specified
            if parsed_args.package_filter:
                findings = self._filter_by_package(findings, parsed_args.package_filter)

            if parsed_args.cve_filter:
                cve_list = [cve.strip() for cve in parsed_args.cve_filter.split(',')]
                findings = self._filter_by_cve(findings, cve_list)

            # Format and output results
            if findings:
                output = format_scan_results(findings, parsed_args.output_format)
                sys.stdout.write(output)
                sys.stdout.write("\n")

                # Summary
                if parsed_args.output_format == 'table':
                    sys.stdout.write(f"\nTotal vulnerabilities found: {len(findings)}\n")
                    self._print_summary_by_severity(findings)
            else:
                sys.stdout.write("No vulnerabilities found matching the specified criteria.\n")

            return 0

        except Exception as e:
            sys.stderr.write(f"Error performing scan: {str(e)}\n")
            return 1

    def _scan_container_image(self, parsed_args, parsed_globals, severity_filter):
        """Scan a container image for vulnerabilities"""
        ecr_client = get_ecr_client(self._session, parsed_globals)
        inspector_client = get_inspector_client(self._session, parsed_globals)

        # Parse the image URI
        parts = parsed_args.image_uri.split('/')
        registry = parts[0]
        repo_tag = '/'.join(parts[1:])
        repo_parts = repo_tag.rsplit(':', 1)
        repository = repo_parts[0]
        tag = repo_parts[1] if len(repo_parts) > 1 else 'latest'

        # Trigger or get scan results from ECR
        try:
            # First try to get existing scan results
            response = ecr_client.describe_image_scan_findings(
                repositoryName=repository,
                imageId={'imageTag': tag}
            )

            scan_status = response.get('imageScanStatus', {}).get('status')

            if scan_status == 'IN_PROGRESS' and parsed_args.wait:
                sys.stdout.write("Scan in progress. Waiting for completion...\n")
                response = self._wait_for_scan_completion(
                    ecr_client, repository, tag, parsed_args.max_wait_time
                )
            elif scan_status != 'COMPLETE':
                # Trigger a new scan
                sys.stdout.write("Initiating vulnerability scan...\n")
                ecr_client.start_image_scan(
                    repositoryName=repository,
                    imageId={'imageTag': tag}
                )

                if parsed_args.wait:
                    response = self._wait_for_scan_completion(
                        ecr_client, repository, tag, parsed_args.max_wait_time
                    )
                else:
                    sys.stdout.write(
                        "Scan initiated. Use --wait to wait for results.\n"
                    )
                    return []

        except ecr_client.exceptions.ImageNotFoundException:
            raise ScanError(f"Image not found: {parsed_args.image_uri}")
        except ecr_client.exceptions.ScanNotFoundException:
            # No scan exists, trigger one
            sys.stdout.write("Initiating vulnerability scan...\n")
            ecr_client.start_image_scan(
                repositoryName=repository,
                imageId={'imageTag': tag}
            )

            if parsed_args.wait:
                response = self._wait_for_scan_completion(
                    ecr_client, repository, tag, parsed_args.max_wait_time
                )
            else:
                sys.stdout.write(
                    "Scan initiated. Use --wait to wait for results.\n"
                )
                return []

        # Process scan findings
        findings = []
        scan_findings = response.get('imageScanFindings', {})

        for finding in scan_findings.get('findings', []):
            severity = finding.get('severity', 'UNKNOWN')

            if not severity_filter or severity in severity_filter:
                finding_data = {
                    'severity': severity,
                    'cveId': finding.get('name', 'N/A'),
                    'description': finding.get('description', ''),
                    'packageName': 'N/A',
                    'packageVersion': 'N/A',
                    'uri': finding.get('uri', '')
                }

                # Extract package information from attributes
                for attribute in finding.get('attributes', []):
                    if attribute['key'] == 'package_name':
                        finding_data['packageName'] = attribute['value']
                    elif attribute['key'] == 'package_version':
                        finding_data['packageVersion'] = attribute['value']

                findings.append(finding_data)

        return findings

    def _scan_resource(self, parsed_args, parsed_globals, severity_filter):
        """Scan a general AWS resource for vulnerabilities"""
        inspector_client = get_inspector_client(self._session, parsed_globals)
        resource_type = validate_resource_arn(parsed_args.resource_arn)

        # Use Inspector v2 API to scan the resource
        try:
            # List findings for the resource
            response = inspector_client.list_findings(
                filterCriteria={
                    'resourceId': [
                        {
                            'comparison': 'EQUALS',
                            'value': parsed_args.resource_arn
                        }
                    ]
                }
            )

            findings = []
            for finding in response.get('findings', []):
                severity = finding.get('severity', 'UNKNOWN')

                if not severity_filter or severity in severity_filter:
                    finding_data = {
                        'severity': severity,
                        'cveId': finding.get('title', 'N/A'),
                        'description': finding.get('description', ''),
                        'packageName': finding.get('packageVulnerabilityDetails', {})
                                             .get('vulnerablePackages', [{}])[0]
                                             .get('name', 'N/A'),
                        'packageVersion': finding.get('packageVulnerabilityDetails', {})
                                                .get('vulnerablePackages', [{}])[0]
                                                .get('version', 'N/A'),
                        'remediation': finding.get('remediation', {})
                                             .get('recommendation', {})
                                             .get('text', '')
                    }
                    findings.append(finding_data)

            return findings

        except Exception as e:
            raise ScanError(f"Failed to scan resource: {str(e)}")

    def _wait_for_scan_completion(self, ecr_client, repository, tag, max_wait_time):
        """Wait for an ECR image scan to complete"""
        start_time = time.time()
        poll_interval = 5  # seconds

        while time.time() - start_time < max_wait_time:
            try:
                response = ecr_client.describe_image_scan_findings(
                    repositoryName=repository,
                    imageId={'imageTag': tag}
                )

                status = response.get('imageScanStatus', {}).get('status')

                if status == 'COMPLETE':
                    return response
                elif status == 'FAILED':
                    raise ScanError(
                        f"Scan failed: {response.get('imageScanStatus', {}).get('description')}"
                    )

                time.sleep(poll_interval)

            except ecr_client.exceptions.ScanNotFoundException:
                # Scan not started yet
                time.sleep(poll_interval)

        raise ScanError(f"Scan did not complete within {max_wait_time} seconds")

    def _filter_by_package(self, findings, package_filter):
        """Filter findings by package name"""
        return [
            f for f in findings
            if package_filter.lower() in f.get('packageName', '').lower()
        ]

    def _filter_by_cve(self, findings, cve_list):
        """Filter findings by CVE ID"""
        return [
            f for f in findings
            if f.get('cveId') in cve_list
        ]

    def _print_summary_by_severity(self, findings):
        """Print a summary of findings by severity"""
        severity_counts = {}

        for finding in findings:
            severity = finding.get('severity', 'UNKNOWN')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        sys.stdout.write("\nSummary by severity:\n")
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL']:
            if severity in severity_counts:
                sys.stdout.write(f"  {severity}: {severity_counts[severity]}\n")