**To update a Control Tower landing zone**

The following ``update-landing-zone`` example updates AWS Control Tower landing zone. ::

    aws controltower update-landing-zone \
        --landing-zone-identifier arn:aws:controltower:us-west-2:123456789012:landingzone/13CJG46WZKXXX4X5 \
        --landing-zone-version 3.3 \
        --manifest "file://UpdateLandingZoneManifest.json"

Contents of ``UpdateLandingZoneManifest.json``::

    {
        "governedRegions": [
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
            "accountId": "123456789222",
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
            "accountId": "123456789111"
        },
        "accessManagement": {
            "enabled": true
        }
    }

Output::

    {
        "operationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Getting started with AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/userguide/getting-started-with-control-tower.html>`__ in the *AWS Control Tower User Guide*.
