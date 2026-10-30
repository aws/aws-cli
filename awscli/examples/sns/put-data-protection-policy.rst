**Example 1: To deny publishers from publishing messages with CreditCardNumber**

The following ``put-data-protection-policy`` example denies publishers from publishing messages with CreditCardNumber. ::

    aws sns put-data-protection-policy \
        --resource-arn arn:aws:sns:us-west-2:123456789012:mytopic \
        --data-protection-policy "{\"Name\":\"data_protection_policy\",\"Description\":\"Example data protection policy\",\"Version\":\"2021-06-01\",\"Statement\":[{\"DataDirection\":\"Inbound\",\"Principal\":[\"*\"],\"DataIdentifier\":[\"arn:aws:dataprotection::aws:data-identifier/CreditCardNumber\"],\"Operation\":{\"Deny\":{}}}]}"

This command produces no output.

For more information, see `Understanding Amazon SNS data protection policies <https://docs.aws.amazon.com/sns/latest/dg/sns-message-data-protection-policies.html>`__ in the *Amazon Simple Notification Service Developer Guide*.

**Example 2: To load parameters from a file**

The following ``put-data-protection-policy`` example loads parameters from a file. ::

    aws sns put-data-protection-policy \
        --resource-arn arn:aws:sns:us-west-2:123456789012:MyTopic \
        --data-protection-policy file://policy.json

Contents of ``policy.json``::

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

This command produces no output.

For more information, see `Understanding Amazon SNS data protection policies <https://docs.aws.amazon.com/sns/latest/dg/sns-message-data-protection-policies.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
