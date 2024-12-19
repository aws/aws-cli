**To Returns list of all CloudWatch Logs account policies**

The following ``describe-account-policies`` example returns a list of all CloudWatch Logs account policies in the account. ::

    aws logs describe-account-policies \
        --policy-type DATA_PROTECTION_POLICY

Output::

    {
        "accountPolicies": [
            {
                "policyName": "Example_Data_Protection_Policy",
                "policyDocument": "{\n\"Name\": \"ACCOUNT_DATA_PROTECTION_POLICY\",\n\"Description\": \"\",\n\"Version\": \"2021-06-01\",\n\"Statement\": [{\n\"Sid\": \"audit-policy\",\n\"DataIdentifier\": [\"arn:aws:dataprotection::aws:data-identifier/Address\", \"arn:aws:dataprotection::aws:data-identifier/CreditCardNumber\", \"arn:aws:dataprotection::aws:data-identifier/DriversLicense-US\", \"arn:aws:dataprotection::aws:data-identifier/EmailAddress\"],\n\"Operation\": {\n\"Audit\": {\n\"FindingsDestination\": {\n\"CloudWatchLogs\": {\n\"LogGroup\": \"AuditLogGroup\"\n}\n}\n}\n}\n}, {\n\"Sid\": \"redact-policy\",\n\"DataIdentifier\": [\"arn:aws:dataprotection::aws:data-identifier/Address\", \"arn:aws:dataprotection::aws:data-identifier/CreditCardNumber\", \"arn:aws:dataprotection::aws:data-identifier/DriversLicense-US\", \"arn:aws:dataprotection::aws:data-identifier/EmailAddress\"],\n\"Operation\": {\n\"Deidentify\": {\n\"MaskConfig\": {}\n}\n}\n}]\n}\n",
                "lastUpdatedTime": 1724944519097,
                "policyType": "DATA_PROTECTION_POLICY",
                "scope": "ALL",
                "accountId": "123456789012"
            }
        ]
    }

For more information, see `Account-level subscription filters <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/SubscriptionFilters-AccountLevel.html>`__ in the *Amazon CloudWatch Logs User Guide*.