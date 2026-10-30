**To create a Control Tower landing zone**

The following ``create-landing-zone`` example creates AWS Control Tower landing zone. ::

    aws controltower create-landing-zone \
        --landing-zone-version 3.3 \
        --manifest "file://LandingZoneManifest.json"

Contents of ``LandingZoneManifest.json``::

    {
        "governedRegions": [
            "us-east-1",
            "us-west-2"
        ],
        "organizationStructure": {
            "security": {
                "name": "Security"
            },
            "sandbox": {
                "name": "Sandbox"
            }
        },
        "centralizedLogging": {
            "accountId": "111122223333",
            "configurations": {
                "loggingBucket": {
                    "retentionDays": 365
                },
                "accessLoggingBucket": {
                    "retentionDays": 3650
                }
            },
            "enabled": true
        },
        "securityRoles": {
            "accountId": "444455556666"
        },
        "accessManagement": {
            "enabled": true
        }
    }

Output::

    {
        "arn": "arn:aws:controltower:us-east-1:123456789012:landingzone/13CJG46WZKXXX4X5",
        "operationIdentifier": "55XXXXXX-e2XX-41XX-a7XX-446XXXXXXXXX"
    }

For more information, see `Getting started with AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/userguide/getting-started-with-control-tower.html>`__ in the *AWS Control Tower User Guide*.
