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
    get_ecr_client, get_lambda_client, get_s3_client,
    format_sbom_output, validate_resource_arn
)


class GenerateSBOMCommand(BasicCommand):
    NAME = 'generate-sbom'

    DESCRIPTION = (
        "Generate a Software Bill of Materials (SBOM) for AWS resources. "
        "This command supports container images in ECR, Lambda functions, "
        "and other package-based resources. The SBOM can be generated in "
        "multiple formats including SPDX and CycloneDX."
    )

    ARG_TABLE = [
        {
            'name': 'resource-arn',
            'help_text': (
                "The ARN of the resource to generate an SBOM for. "
                "This can be an ECR repository, Lambda function, or other "
                "supported AWS resource."
            ),
            'required': False
        },
        {
            'name': 'image-uri',
            'help_text': (
                "The URI of a container image in ECR to generate an SBOM for. "
                "Format: <registry>/<repository>:<tag>"
            ),
            'required': False
        },
        {
            'name': 'format',
            'help_text': (
                "The output format for the SBOM. Supported formats: "
                "spdx-json, spdx-yaml, cyclonedx-json, cyclonedx-xml"
            ),
            'default': 'spdx-json',
            'choices': ['spdx-json', 'spdx-yaml', 'cyclonedx-json', 'cyclonedx-xml']
        },
        {
            'name': 'output',
            'help_text': (
                "The file path to write the SBOM to. If not specified, "
                "the SBOM will be written to stdout."
            ),
            'required': False
        },
        {
            'name': 'upload',
            'action': 'store_true',
            'help_text': (
                "Upload the generated SBOM to S3. The SBOM will be stored "
                "in the default supply chain bucket for the account."
            )
        },
        {
            'name': 's3-bucket',
            'help_text': (
                "The S3 bucket to upload the SBOM to (only used with --upload). "
                "If not specified, a default bucket will be used."
            ),
            'required': False
        },
        {
            'name': 'scan-depth',
            'help_text': (
                "The depth to scan for dependencies. Use 'all' for complete "
                "dependency tree or specify a number for limited depth."
            ),
            'default': 'all'
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
            if parsed_args.image_uri:
                sbom_data = self._generate_sbom_for_image(
                    parsed_args, parsed_globals
                )
            else:
                sbom_data = self._generate_sbom_for_resource(
                    parsed_args, parsed_globals
                )

            # Format the SBOM according to the requested format
            formatted_sbom = format_sbom_output(sbom_data, parsed_args.format)

            # Output or save the SBOM
            if parsed_args.output:
                with open(parsed_args.output, 'w') as f:
                    f.write(formatted_sbom)
                sys.stdout.write(f"SBOM written to {parsed_args.output}\n")
            else:
                sys.stdout.write(formatted_sbom)
                sys.stdout.write("\n")

            # Upload to S3 if requested
            if parsed_args.upload:
                s3_key = self._upload_sbom_to_s3(
                    formatted_sbom, parsed_args, parsed_globals
                )
                sys.stdout.write(f"SBOM uploaded to S3: {s3_key}\n")

            return 0

        except Exception as e:
            sys.stderr.write(f"Error generating SBOM: {str(e)}\n")
            return 1

    def _generate_sbom_for_image(self, parsed_args, parsed_globals):
        """Generate SBOM for a container image in ECR"""
        ecr_client = get_ecr_client(self._session, parsed_globals)

        # Parse the image URI
        parts = parsed_args.image_uri.split('/')
        registry = parts[0]
        repo_tag = '/'.join(parts[1:])
        repo_parts = repo_tag.rsplit(':', 1)
        repository = repo_parts[0]
        tag = repo_parts[1] if len(repo_parts) > 1 else 'latest'

        # Get image manifest and scan results
        response = ecr_client.batch_get_image(
            repositoryName=repository,
            imageIds=[{'imageTag': tag}]
        )

        if not response.get('images'):
            raise ValueError(f"Image not found: {parsed_args.image_uri}")

        image = response['images'][0]

        # Get vulnerability scan results if available
        scan_findings = None
        try:
            scan_response = ecr_client.describe_image_scan_findings(
                repositoryName=repository,
                imageId={'imageTag': tag}
            )
            scan_findings = scan_response.get('imageScanFindings')
        except:
            pass

        # Build SBOM data structure
        sbom_data = {
            'spdxVersion': 'SPDX-2.3',
            'creationInfo': {
                'created': datetime.utcnow().isoformat() + 'Z',
                'creators': ['Tool: aws-cli-supplychain']
            },
            'name': f"SBOM for {parsed_args.image_uri}",
            'packages': self._extract_packages_from_image(image, scan_findings),
            'relationships': []
        }

        return sbom_data

    def _generate_sbom_for_resource(self, parsed_args, parsed_globals):
        """Generate SBOM for a general AWS resource"""
        resource_type = validate_resource_arn(parsed_args.resource_arn)

        if 'lambda' in resource_type:
            return self._generate_sbom_for_lambda(parsed_args, parsed_globals)
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")

    def _generate_sbom_for_lambda(self, parsed_args, parsed_globals):
        """Generate SBOM for a Lambda function"""
        lambda_client = get_lambda_client(self._session, parsed_globals)

        # Parse function name from ARN
        arn_parts = parsed_args.resource_arn.split(':')
        function_name = arn_parts[-1]

        # Get function configuration
        response = lambda_client.get_function(FunctionName=function_name)

        # Build SBOM data
        sbom_data = {
            'spdxVersion': 'SPDX-2.3',
            'creationInfo': {
                'created': datetime.utcnow().isoformat() + 'Z',
                'creators': ['Tool: aws-cli-supplychain']
            },
            'name': f"SBOM for Lambda function {function_name}",
            'packages': self._extract_packages_from_lambda(response),
            'relationships': []
        }

        return sbom_data

    def _extract_packages_from_image(self, image, scan_findings):
        """Extract package information from container image"""
        packages = []

        # Extract from scan findings if available
        if scan_findings and scan_findings.get('findings'):
            for finding in scan_findings['findings']:
                for attribute in finding.get('attributes', []):
                    if attribute['key'] == 'package_name':
                        package = {
                            'name': attribute['value'],
                            'SPDXID': f"SPDXRef-Package-{attribute['value']}",
                        }
                        # Add version if available
                        for attr in finding['attributes']:
                            if attr['key'] == 'package_version':
                                package['versionInfo'] = attr['value']
                                break
                        packages.append(package)
                        break

        # If no scan findings, create a basic package entry
        if not packages:
            packages.append({
                'name': 'container-image',
                'SPDXID': 'SPDXRef-Package-Container',
                'downloadLocation': 'NOASSERTION'
            })

        return packages

    def _extract_packages_from_lambda(self, function_info):
        """Extract package information from Lambda function"""
        packages = []

        config = function_info.get('Configuration', {})

        # Add the Lambda function itself as a package
        packages.append({
            'name': config.get('FunctionName', 'unknown'),
            'SPDXID': 'SPDXRef-Package-Lambda',
            'versionInfo': config.get('Version', '$LATEST'),
            'downloadLocation': config.get('CodeSha256', 'NOASSERTION')
        })

        # Add runtime as a dependency
        if config.get('Runtime'):
            packages.append({
                'name': f"runtime-{config['Runtime']}",
                'SPDXID': f"SPDXRef-Package-Runtime-{config['Runtime']}",
                'downloadLocation': 'NOASSERTION'
            })

        # Add layers as dependencies
        for i, layer in enumerate(config.get('Layers', [])):
            packages.append({
                'name': f"layer-{i}",
                'SPDXID': f"SPDXRef-Package-Layer-{i}",
                'downloadLocation': layer,
            })

        return packages

    def _upload_sbom_to_s3(self, sbom_content, parsed_args, parsed_globals):
        """Upload SBOM to S3"""
        s3_client = get_s3_client(self._session, parsed_globals)

        # Determine bucket name
        bucket = parsed_args.s3_bucket
        if not bucket:
            # Use default bucket pattern
            account_id = self._session.get_credentials().access_key[:12]
            region = parsed_globals.region or 'us-east-1'
            bucket = f"aws-supplychain-sboms-{account_id}-{region}"

        # Generate key name
        timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
        if parsed_args.image_uri:
            resource_id = parsed_args.image_uri.replace('/', '-').replace(':', '-')
        else:
            resource_id = parsed_args.resource_arn.split(':')[-1]

        key = f"sboms/{resource_id}/{timestamp}.{parsed_args.format}"

        # Upload to S3
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=sbom_content.encode('utf-8'),
            ContentType='application/json' if 'json' in parsed_args.format else 'text/plain'
        )

        return f"s3://{bucket}/{key}"