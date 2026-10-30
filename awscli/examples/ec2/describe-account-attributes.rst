**Example 1: To describe all the attributes for your AWS account**

The following ``describe-account-attributes`` example describes the attributes for your AWS account. ::

    aws ec2 describe-account-attributes

Output::

    {
        "AccountAttributes": [
            {
                "AttributeName": "vpc-max-security-groups-per-interface",
                "AttributeValues": [
                    {
                        "AttributeValue": "5"
                    }
                ]
            },
            {
                "AttributeName": "max-instances",
                "AttributeValues": [
                    {
                        "AttributeValue": "20"
                    }
                ]
            },
            {
                "AttributeName": "supported-platforms",
                "AttributeValues": [
                    {
                        "AttributeValue": "EC2"
                    },
                    {
                        "AttributeValue": "VPC"
                    }
                ]
            },
            {
                "AttributeName": "default-vpc",
                "AttributeValues": [
                    {
                        "AttributeValue": "none"
                    }
                ]
            },
            {
                "AttributeName": "max-elastic-ips",
                "AttributeValues": [
                    {
                        "AttributeValue": "5"
                    }
                ]
            },
            {
                "AttributeName": "vpc-max-elastic-ips",
                "AttributeValues": [
                    {
                        "AttributeValue": "5"
                    }
                ]
            }
        ]
    }

For more information, see `Amazon EC2 service quotas <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-resource-limits.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To describe a single attribute for your AWS account**

The following ``describe-account-attributes`` example describes the ``supported-platforms`` attribute for your AWS account. ::

    aws ec2 describe-account-attributes \
        --attribute-names supported-platforms

Output::

    {
        "AccountAttributes": [
            {
                "AttributeName": "supported-platforms",
                "AttributeValues": [
                    {
                        "AttributeValue": "EC2"
                    },
                    {
                        "AttributeValue": "VPC"
                    }
                ]
            }
        ]
    }

For more information, see `Amazon EC2 service quotas <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-resource-limits.html>`__ in the *Amazon EC2 User Guide*.
