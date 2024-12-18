**To Create an account-level data protection policy or subscription filter policy**

The following ``put-account-policy`` example creates account-level data protection policy. ::

    aws logs put-account-policy \
        --policy-name Example_Data_Protection_Policy \
        --policy-document file://policy.json \
        --policy-type DATA_PROTECTION_POLICY \
        --scope ALL

The file ``policy.json`` is a JSON document in the current folder.

    {
        "Name": "ACCOUNT_DATA_PROTECTION_POLICY",
        "Description": "",
        "Version": "2021-06-01",
        "Statement": [{
            "Sid": "audit-policy",
            "DataIdentifier": ["arn:aws:dataprotection::aws:data-identifier/Address", "arn:aws:dataprotection::aws:data-identifier/CreditCardNumber", "arn:aws:dataprotection::aws:data-identifier/DriversLicense-US", "arn:aws:dataprotection::aws:data-identifier/EmailAddress"],
            "Operation": {
                "Audit": {
                    "FindingsDestination": {
                        "CloudWatchLogs": {
                            "LogGroup": "AuditLogGroup"
                        }
                    }
                }
            }
        }, {
            "Sid": "redact-policy",
            "DataIdentifier": ["arn:aws:dataprotection::aws:data-identifier/Address", "arn:aws:dataprotection::aws:data-identifier/CreditCardNumber", "arn:aws:dataprotection::aws:data-identifier/DriversLicense-US", "arn:aws:dataprotection::aws:data-identifier/EmailAddress"],
            "Operation": {
                "Deidentify": {
                    "MaskConfig": {}
                }
            }
        }]
    }

Output::

    {
        "accountPolicy": {
            "policyName": "Example_Data_Protection_Policy",
            "policyDocument": "{\n\"Name\": \"ACCOUNT_DATA_PROTECTION_POLICY\",\n\"Description\": \"\",\n\"Version\": \"2021-06-01\",\n\"Statement\": [{\n\"Sid\": \"audit-policy\",\n\"DataIdentifier\": [\"arn:aws:dataprotection::aws:data-identifier/Address\", \"arn:aws:dataprotection::aws:data-identifier/CreditCardNumber\", \"arn:aws:dataprotection::aws:data-identifier/DriversLicense-US\", \"arn:aws:dataprotection::aws:data-identifier/EmailAddress\"],\n\"Operation\": {\n\"Audit\": {\n\"FindingsDestination\": {\n\"CloudWatchLogs\": {\n\"LogGroup\": \"AuditLogGroup\"\n}\n}\n}\n}\n}, {\n\"Sid\": \"redact-policy\",\n\"DataIdentifier\": [\"arn:aws:dataprotection::aws:data-identifier/Address\", \"arn:aws:dataprotection::aws:data-identifier/CreditCardNumber\", \"arn:aws:dataprotection::aws:data-identifier/DriversLicense-US\", \"arn:aws:dataprotection::aws:data-identifier/EmailAddress\"],\n\"Operation\": {\n\"Deidentify\": {\n\"MaskConfig\": {}\n}\n}\n}]\n}\n",
            "lastUpdatedTime": 1724941132142,
            "policyType": "DATA_PROTECTION_POLICY",
            "scope": "ALL"
        }
    }

For more information, see `Account-level subscription filters <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/SubscriptionFilters-AccountLevel.html>`__ in the *Amazon CloudWatch Logs User Guide*.