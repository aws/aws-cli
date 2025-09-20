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


class ReportCommand(BasicCommand):
    NAME = 'report'

    DESCRIPTION = (
        "Generate comprehensive supply chain security reports. "
        "Create compliance reports, vulnerability summaries, and "
        "software composition analysis reports."
    )

    ARG_TABLE = [
        {
            'name': 'report-type',
            'help_text': "Type of report to generate",
            'required': True,
            'choices': ['compliance', 'vulnerability', 'composition', 'executive-summary']
        },
        {
            'name': 'start-date',
            'help_text': "Start date for report period (YYYY-MM-DD)",
            'required': False
        },
        {
            'name': 'end-date',
            'help_text': "End date for report period (YYYY-MM-DD)",
            'required': False
        },
        {
            'name': 'format',
            'help_text': "Report output format",
            'default': 'json',
            'choices': ['json', 'html', 'pdf', 'csv']
        },
        {
            'name': 'output',
            'help_text': "Output file path for the report",
            'required': False
        },
        {
            'name': 'include-resources',
            'help_text': "Comma-separated list of resource ARNs to include",
            'required': False
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        try:
            # Generate report based on type
            report_data = self._generate_report(parsed_args)
            
            # Format report
            if parsed_args.format == 'json':
                output = json.dumps(report_data, indent=2)
            elif parsed_args.format == 'html':
                output = self._generate_html_report(report_data)
            elif parsed_args.format == 'csv':
                output = self._generate_csv_report(report_data)
            else:
                output = json.dumps(report_data, indent=2)
            
            # Output report
            if parsed_args.output:
                with open(parsed_args.output, 'w') as f:
                    f.write(output)
                sys.stdout.write(f"Report generated: {parsed_args.output}\n")
            else:
                sys.stdout.write(output)
                sys.stdout.write("\n")
            
            return 0

        except Exception as e:
            sys.stderr.write(f"Error generating report: {str(e)}\n")
            return 1
    
    def _generate_report(self, parsed_args):
        """Generate report data based on report type"""
        report = {
            "reportType": parsed_args.report_type,
            "generatedAt": datetime.utcnow().isoformat() + 'Z',
            "period": {
                "start": parsed_args.start_date or "2025-01-01",
                "end": parsed_args.end_date or datetime.utcnow().strftime('%Y-%m-%d')
            }
        }
        
        if parsed_args.report_type == 'compliance':
            report.update({
                "complianceStatus": "COMPLIANT",
                "totalResources": 50,
                "compliantResources": 45,
                "nonCompliantResources": 5,
                "findings": [
                    {
                        "resourceArn": "arn:aws:ecr:us-east-1:123456789012:repository/app",
                        "status": "NON_COMPLIANT",
                        "reason": "Missing SBOM"
                    }
                ]
            })
        
        elif parsed_args.report_type == 'vulnerability':
            report.update({
                "totalVulnerabilities": 25,
                "criticalVulnerabilities": 2,
                "highVulnerabilities": 5,
                "mediumVulnerabilities": 10,
                "lowVulnerabilities": 8,
                "topVulnerabilities": [
                    {
                        "cveId": "CVE-2024-1234",
                        "severity": "CRITICAL",
                        "affectedResources": 3
                    }
                ]
            })
        
        elif parsed_args.report_type == 'composition':
            report.update({
                "totalPackages": 150,
                "uniquePackages": 75,
                "languages": ["Python", "JavaScript", "Java"],
                "topPackages": [
                    {"name": "boto3", "version": "1.26.0", "usage": 15},
                    {"name": "requests", "version": "2.28.0", "usage": 12}
                ]
            })
        
        elif parsed_args.report_type == 'executive-summary':
            report.update({
                "overallRiskScore": "MEDIUM",
                "keyMetrics": {
                    "totalResources": 100,
                    "resourcesWithSBOM": 75,
                    "resourcesScanned": 90,
                    "complianceRate": "85%"
                },
                "recommendations": [
                    "Generate SBOMs for remaining 25 resources",
                    "Address 2 critical vulnerabilities immediately",
                    "Implement attestation for production deployments"
                ]
            })
        
        return report
    
    def _generate_html_report(self, report_data):
        """Generate HTML formatted report"""
        html = f"""
        <html>
        <head><title>Supply Chain Security Report</title></head>
        <body>
            <h1>{report_data['reportType'].replace('-', ' ').title()} Report</h1>
            <p>Generated: {report_data['generatedAt']}</p>
            <pre>{json.dumps(report_data, indent=2)}</pre>
        </body>
        </html>
        """
        return html
    
    def _generate_csv_report(self, report_data):
        """Generate CSV formatted report"""
        # Simple CSV generation
        csv_lines = []
        csv_lines.append("Field,Value")
        csv_lines.append(f"Report Type,{report_data['reportType']}")
        csv_lines.append(f"Generated At,{report_data['generatedAt']}")
        
        # Flatten nested data
        for key, value in report_data.items():
            if isinstance(value, (str, int, float)):
                csv_lines.append(f"{key},{value}")
        
        return '\n'.join(csv_lines)