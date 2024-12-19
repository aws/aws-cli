**To Create a data protection policy for the specified log group**

The following ``put-data-protection-policy`` example creates a data protection policy for the log group named ``demo-log-group``. ::

    aws logs put-data-protection-policy \
        --log-group-identifier demo-log-group \
        --policy-document file://policy.json

The file ``policy.json`` is a JSON document in the current folder.

    {
        "Name": "data-protection-policy",
        "Description": "",
        "Version": "2021-06-01",
        "Statement": [{
            "Sid": "audit-policy",
            "DataIdentifier": ["arn:aws:dataprotection::aws:data-identifier/CreditCardNumber"],
            "Operation": {
                "Audit": {
                    "FindingsDestination": {}
                }
            }
        }, {
            "Sid": "redact-policy",
            "DataIdentifier": ["arn:aws:dataprotection::aws:data-identifier/CreditCardNumber"],
            "Operation": {
                "Deidentify": {
                    "MaskConfig": {}
                }
            }
        }]
    }

Output::

    {
        "logGroupIdentifier": "demo-log-group",
        "policyDocument": "{\n\"Name\": \"data-protection-policy\",\n\"Description\": \"\",\n\"Version\": \"2021-06-01\",\n\"Statement\": [{\n\"Sid\": \"audit-policy\",\n\"DataIdentifier\": [\"arn:aws:dataprotection::aws:data-identifier/CreditCardNumber\"],\n\"Operation\": {\n\"Audit\": {\n\"FindingsDestination\": {}\n}\n}\n}, {\n\"Sid\": \"redact-policy\",\n\"DataIdentifier\": [\"arn:aws:dataprotection::aws:data-identifier/CreditCardNumber\"],\n\"Operation\": {\n\"Deidentify\": {\n\"MaskConfig\": {}\n}\n}\n}]\n}\n",
        "lastUpdatedTime": 1725044223296
    }

For more information, see `Help protect sensitive log data with masking <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/mask-sensitive-log-data.html>`__ in the *Amazon CloudWatch Logs User Guide*.