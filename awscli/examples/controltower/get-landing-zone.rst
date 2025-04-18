**To Describe A Control Tower Landing Zone**

The following ``get-landing-zone`` example get details of AWS Control Tower Landing Zone::

    aws controltower get-landing-zone \
        --landing-zone-identifier arn:aws:controltower:us-east-1:123456789012:landingzone/13CJG46WZKXXX4X5

Output::

    {
        "landingZone": {
            "arn": "arn:aws:controltower:us-east-1:123456789012:landingzone/13CJG46WZKXXX4X5",
            "driftStatus": {
                "status": "IN_SYNC"
            },
            "latestAvailableVersion": "3.3",
            "manifest": {
                "accessManagement": {
                    "enabled": true
                },
                "securityRoles": {
                    "accountId": "098765432101"
                },
                "governedRegions": [
                    "us-east-1",
                    "us-west-2"
                ],
                "organizationStructure": {
                    "security": {
                        "name": "Security"
                    }
                },
                "centralizedLogging": {
                    "accountId": "543210987654",
                    "configurations": {
                        "loggingBucket": {
                            "retentionDays": 365
                        },
                        "kmsKeyArn": "<arn_of_kms_key",
                        "accessLoggingBucket": {
                            "retentionDays": 3650
                        }
                    },
                    "enabled": true
                }
            },
            "status": "ACTIVE",
            "version": "3.3"
        }
    }
For more information, see `AWS Control Tower Getting Started <https://docs.aws.amazon.com/controltower/latest/userguide/getting-started-with-control-tower.html>`__ in the *AWS Control Tower User Guide*.