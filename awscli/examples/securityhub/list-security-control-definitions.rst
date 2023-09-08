**Example 1: To list available security controls**

The following ``list-security-control-definitions`` example lists the available security controls across all Security Hub standards. This example limits the results to three controls. ::

    aws securityhub list-security-control-definitions \
        --max-items 3

Output::

    {
        "SecurityControlDefinitions": [
            {
                "SecurityControlId": "ACM.1",
                "Title": "Imported and ACM-issued certificates should be renewed after a specified time period",
                "Description": "This AWS control checks whether ACM Certificates in your account are marked for expiration within a specified time period. Certificates provided by ACM are automatically renewed. ACM does not automatically renew certificates that you import.",
                "RemediationUrl": "https://docs.aws.amazon.com/console/securityhub/ACM.1/remediation",
                "SeverityRating": "MEDIUM",
                "CurrentRegionAvailability": "AVAILABLE"
            },
            {
                "SecurityControlId": "ACM.2",
                "Title": "RSA certificates managed by ACM should use a key length of at least 2,048 bits",
                "Description": "This control checks whether RSA certificates managed by AWS Certificate Manager use a key length of at least 2,048 bits. The control fails if the key length is smaller than 2,048 bits.",
                "RemediationUrl": "https://docs.aws.amazon.com/console/securityhub/ACM.2/remediation",
                "SeverityRating": "HIGH",
                "CurrentRegionAvailability": "AVAILABLE"
            },
            {
                "SecurityControlId": "APIGateway.1",
                "Title": "API Gateway REST and WebSocket API execution logging should be enabled",
                "Description": "This control checks whether all stages of Amazon API Gateway REST and WebSocket APIs have logging enabled. The control fails if logging is not enabled for all methods of a stage or if loggingLevel is neither ERROR nor INFO.",
                "RemediationUrl": "https://docs.aws.amazon.com/console/securityhub/APIGateway.1/remediation",
                "SeverityRating": "MEDIUM",
                "CurrentRegionAvailability": "AVAILABLE"
            }
        ],
        "NextToken": "U2FsdGVkX1/UprCPzxVbkDeHikDXbDxfgJZ1w2RG1XWsFPTMTIQPVE0m/FduIGxS7ObRtAbaUt/8/RCQcg2PU0YXI20hH/GrhoOTgv+TSm0qvQVFhkJepWmqh+NYawjocVBeos6xzn/8qnbF9IuwGg=="
    }

For more information, see `Viewing details for a standard <https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-standards-view-controls.html>`__ in the *AWS Security Hub User Guide*.

**Example 2: To list available security controls for a specific standard**

The following ``list-security-control-definitions`` example lists the available security controls for the CIS AWS Foundations Benchmark v1.4.0. This example limits the results to three controls. ::

    aws securityhub list-security-control-definitions \
        --standards-arn "arn:aws:securityhub:us-east-1::standards/cis-aws-foundations-benchmark/v/1.4.0" \
        --max-items 3

Output::

    {
        "SecurityControlDefinitions": [
            {
                "SecurityControlId": "CloudTrail.1",
                "Title": "CloudTrail should be enabled and configured with at least one multi-Region trail that includes read and write management events",
                "Description": "This AWS control checks that there is at least one multi-region AWS CloudTrail trail includes read and write management events.",
                "RemediationUrl": "https://docs.aws.amazon.com/console/securityhub/CloudTrail.1/remediation",
                "SeverityRating": "HIGH",
                "CurrentRegionAvailability": "AVAILABLE"
            },
            {
                "SecurityControlId": "CloudTrail.2",
                "Title": "CloudTrail should have encryption at-rest enabled",
                "Description": "This AWS control checks whether AWS CloudTrail is configured to use the server side encryption (SSE) AWS Key Management Service (AWS KMS) customer master key (CMK) encryption. The check will pass if the KmsKeyId is defined.",
                "RemediationUrl": "https://docs.aws.amazon.com/console/securityhub/CloudTrail.2/remediation",
                "SeverityRating": "MEDIUM",
                "CurrentRegionAvailability": "AVAILABLE"
            },
            {
                "SecurityControlId": "CloudTrail.4",
                "Title": "CloudTrail log file validation should be enabled",
                "Description": "This AWS control checks whether CloudTrail log file validation is enabled.",
                "RemediationUrl": "https://docs.aws.amazon.com/console/securityhub/CloudTrail.4/remediation",
                "SeverityRating": "MEDIUM",
                "CurrentRegionAvailability": "AVAILABLE"
            }
        ],
        "NextToken": "eyJOZXh0VG9rZW4iOiBudWxsLCAiYm90b190cnVuY2F0ZV9hbW91bnQiOiAzfQ=="
    }

For more information, see `Viewing details for a standard <https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-standards-view-controls.html>`__ in the *AWS Security Hub User Guide*.