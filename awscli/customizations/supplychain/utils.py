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
from xml.etree import ElementTree as ET
from xml.dom import minidom

# Note: yaml support would require PyYAML dependency
# For now, we'll skip YAML output format
try:
    import yaml
except ImportError:
    yaml = None


def get_ecr_client(session, parsed_globals):
    """Get an ECR client with the appropriate configuration"""
    return session.create_client(
        'ecr',
        region_name=parsed_globals.region,
        endpoint_url=parsed_globals.endpoint_url,
        verify=parsed_globals.verify_ssl
    )


def get_lambda_client(session, parsed_globals):
    """Get a Lambda client with the appropriate configuration"""
    return session.create_client(
        'lambda',
        region_name=parsed_globals.region,
        endpoint_url=parsed_globals.endpoint_url,
        verify=parsed_globals.verify_ssl
    )


def get_s3_client(session, parsed_globals):
    """Get an S3 client with the appropriate configuration"""
    return session.create_client(
        's3',
        region_name=parsed_globals.region,
        endpoint_url=parsed_globals.endpoint_url,
        verify=parsed_globals.verify_ssl
    )


def get_inspector_client(session, parsed_globals):
    """Get an Inspector client with the appropriate configuration"""
    return session.create_client(
        'inspector2',
        region_name=parsed_globals.region,
        endpoint_url=parsed_globals.endpoint_url,
        verify=parsed_globals.verify_ssl
    )


def get_signer_client(session, parsed_globals):
    """Get a Signer client with the appropriate configuration"""
    return session.create_client(
        'signer',
        region_name=parsed_globals.region,
        endpoint_url=parsed_globals.endpoint_url,
        verify=parsed_globals.verify_ssl
    )


def get_ssm_client(session, parsed_globals):
    """Get a Systems Manager client with the appropriate configuration"""
    return session.create_client(
        'ssm',
        region_name=parsed_globals.region,
        endpoint_url=parsed_globals.endpoint_url,
        verify=parsed_globals.verify_ssl
    )


def validate_resource_arn(arn):
    """Validate and parse an AWS resource ARN"""
    if not arn or not arn.startswith('arn:'):
        raise ValueError(f"Invalid ARN format: {arn}")

    parts = arn.split(':')
    if len(parts) < 6:
        raise ValueError(f"Invalid ARN format: {arn}")

    return parts[2]  # Return the service name


def format_sbom_output(sbom_data, format_type):
    """Format SBOM data according to the specified format"""
    if format_type == 'spdx-json':
        return json.dumps(sbom_data, indent=2)

    elif format_type == 'spdx-yaml':
        if yaml is None:
            raise ValueError("YAML format requires PyYAML to be installed")
        return yaml.dump(sbom_data, default_flow_style=False)

    elif format_type == 'cyclonedx-json':
        # Convert SPDX to CycloneDX format
        cyclonedx_data = convert_spdx_to_cyclonedx(sbom_data)
        return json.dumps(cyclonedx_data, indent=2)

    elif format_type == 'cyclonedx-xml':
        # Convert SPDX to CycloneDX XML format
        cyclonedx_data = convert_spdx_to_cyclonedx(sbom_data)
        return convert_to_cyclonedx_xml(cyclonedx_data)

    else:
        raise ValueError(f"Unsupported format: {format_type}")


def convert_spdx_to_cyclonedx(spdx_data):
    """Convert SPDX format to CycloneDX format"""
    cyclonedx = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "serialNumber": f"urn:uuid:{spdx_data.get('name', 'unknown')}",
        "version": 1,
        "metadata": {
            "timestamp": spdx_data.get('creationInfo', {}).get('created'),
            "tools": [
                {
                    "vendor": "AWS",
                    "name": "aws-cli-supplychain",
                    "version": "1.0.0"
                }
            ]
        },
        "components": []
    }

    # Convert packages to components
    for package in spdx_data.get('packages', []):
        component = {
            "type": "library",
            "bom-ref": package.get('SPDXID', ''),
            "name": package.get('name', ''),
            "version": package.get('versionInfo', 'unknown')
        }
        cyclonedx['components'].append(component)

    return cyclonedx


def convert_to_cyclonedx_xml(cyclonedx_data):
    """Convert CycloneDX JSON to XML format"""
    root = ET.Element('bom')
    root.set('xmlns', 'http://cyclonedx.org/schema/bom/1.4')
    root.set('version', str(cyclonedx_data.get('version', 1)))

    # Add metadata
    metadata = ET.SubElement(root, 'metadata')
    timestamp = ET.SubElement(metadata, 'timestamp')
    timestamp.text = cyclonedx_data.get('metadata', {}).get('timestamp', '')

    # Add components
    components = ET.SubElement(root, 'components')
    for comp in cyclonedx_data.get('components', []):
        component = ET.SubElement(components, 'component')
        component.set('type', comp.get('type', 'library'))
        component.set('bom-ref', comp.get('bom-ref', ''))

        name = ET.SubElement(component, 'name')
        name.text = comp.get('name', '')

        version = ET.SubElement(component, 'version')
        version.text = comp.get('version', '')

    # Pretty print the XML
    rough_string = ET.tostring(root, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def parse_severity_filter(severity_string):
    """Parse a comma-separated severity filter string"""
    if not severity_string:
        return []

    severities = [s.strip().upper() for s in severity_string.split(',')]
    valid_severities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL']

    for severity in severities:
        if severity not in valid_severities:
            raise ValueError(f"Invalid severity level: {severity}")

    return severities


def format_scan_results(findings, output_format='table'):
    """Format vulnerability scan results for display"""
    if output_format == 'json':
        return json.dumps(findings, indent=2)

    elif output_format == 'table':
        # Format as a simple table
        lines = []
        lines.append("Severity    | CVE ID         | Package        | Version")
        lines.append("-" * 60)

        for finding in findings:
            severity = finding.get('severity', 'UNKNOWN')
            cve_id = finding.get('cveId', 'N/A')
            package = finding.get('packageName', 'N/A')
            version = finding.get('packageVersion', 'N/A')

            lines.append(f"{severity:11} | {cve_id:14} | {package:14} | {version}")

        return '\n'.join(lines)

    else:
        raise ValueError(f"Unsupported output format: {output_format}")


def create_default_policy():
    """Create a default supply chain security policy"""
    return {
        "version": "1.0",
        "rules": [
            {
                "id": "no-critical-vulnerabilities",
                "description": "Block deployments with critical vulnerabilities",
                "condition": {
                    "vulnerabilities": {
                        "severity": "CRITICAL",
                        "count": 0
                    }
                },
                "action": "BLOCK"
            },
            {
                "id": "require-sbom",
                "description": "Require SBOM for all deployments",
                "condition": {
                    "sbom": {
                        "required": True
                    }
                },
                "action": "BLOCK"
            },
            {
                "id": "require-attestation",
                "description": "Require signed attestation for production deployments",
                "condition": {
                    "attestation": {
                        "required": True,
                        "types": ["slsa-provenance"]
                    }
                },
                "action": "WARN"
            }
        ]
    }


def validate_policy(policy_data):
    """Validate a supply chain security policy"""
    required_fields = ['version', 'rules']

    for field in required_fields:
        if field not in policy_data:
            raise ValueError(f"Missing required field in policy: {field}")

    for rule in policy_data.get('rules', []):
        if 'id' not in rule or 'action' not in rule:
            raise ValueError("Each policy rule must have 'id' and 'action' fields")

        if rule['action'] not in ['BLOCK', 'WARN', 'ALLOW']:
            raise ValueError(f"Invalid action in rule {rule['id']}: {rule['action']}")

    return True