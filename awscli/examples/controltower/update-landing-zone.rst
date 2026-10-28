**To update a Control Tower landing zone**

The following ``update-landing-zone`` example updates AWS Control Tower landing zone. ::

    aws controltower update-landing-zone \
        --landing-zone-identifier arn:aws:controltower:us-east-1:123456789012:landingzone/13CJG46WZKXXX4X5 \
        --landing-zone-version 3.3 \
        --manifest "file://UpdateLandingZoneManifest.json"

Contents of ``UpdateLandingZoneManifest.json``::

    {
        "governedRegions": [
            "us-east-1",
            "us-west-2",
            "eu-west-1"
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
        "operationIdentifier": "53XXXXXX-b2XX-97XX-c6XX-474XXXXXXXXX"
    }

For more information, see `Getting started with AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/userguide/getting-started-with-control-tower.html>`__ in the *AWS Control Tower User Guide*.
