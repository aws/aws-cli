**To get a data protection policy for an SNS topic**

The following ``get-data-protection-policy`` example retrieves the data protection policy attached to the specified SNS topic. ::

    aws sns get-data-protection-policy \
        --resource-arn arn:aws:sns:us-east-1:123456789012:MyTopic

Output::

    {
        "Name": "data_protection_policy",
        "Description": "Example data protection policy",
        "Version": "2021-06-01",
        "Statement": [
            {
                "DataDirection": "Inbound",
                "Principal": [
                    "*"
                ],
                "DataIdentifier": [
                    "arn:aws:dataprotection::aws:data-identifier/CreditCardNumber"
                ],
                "Operation": {
                    "Deny": {}
                }
            }
        ]
    }
