**To describe your internet gateways**

The following ``describe-internet-gateways`` example retrieves details about all of your internet gateways. ::

    aws ec2 describe-internet-gateways

Output::

    {
        "InternetGateways": [
            {
                "Attachments": [],
                "InternetGatewayId": "igw-036dde5c85EXAMPLE",
                "OwnerId": "111122223333",
                "Tags": []
            },
            {
                "Attachments": [
                    {
                        "State": "available",
                        "VpcId": "vpc-cEXAMPLE"
                    }
                ],
                "InternetGatewayId": "igw-0EXAMPLE",
                "OwnerId": "111122223333",
                "Tags": []
            }
        ]
    }             

For more information, see `Internet Gateways <https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html>`__ in the *AWS VPC User Guide*.
