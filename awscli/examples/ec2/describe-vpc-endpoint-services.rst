**Example 1: To describe all VPC endpoint services**

The following ``describe-vpc-endpoint-services`` example lists all VPC endpoint services for an AWS Region. ::

    aws ec2 describe-vpc-endpoint-services

Output::

    {
        "ServiceDetails": [
            {
                "ServiceType": [
                    {
                        "ServiceType": "Gateway"
                    }
                ],
                "AcceptanceRequired": false,
                "ServiceName": "com.amazonaws.us-west-2.dynamodb",
                "VpcEndpointPolicySupported": true,
                "Owner": "amazon",
                "AvailabilityZones": [
                    "us-west-2a", 
                    "us-west-2b", 
                    "us-west-2c", 
                    "us-west-2d"
                ],
                "BaseEndpointDnsNames": [
                    "dynamodb.us-west-2.amazonaws.com"
                ]
            },
            {
                "ServiceType": [
                    {
                        "ServiceType": "Interface"
                    }
                ],
                "PrivateDnsName": "ec2.us-west-2.amazonaws.com",
                "ServiceName": "com.amazonaws.us-west-2.ec2",
                "VpcEndpointPolicySupported": false,
                "Owner": "amazon",
                "AvailabilityZones": [
                    "us-west-2a", 
                    "us-west-2b", 
                    "us-west-2c", 
                    "us-west-2d"
                ],
                "AcceptanceRequired": false,
                "BaseEndpointDnsNames": [
                    "ec2.us-west-2.vpce.amazonaws.com"
                ]
            },
            {
                "ServiceType": [
                    {
                        "ServiceType": "Interface"
                    }
                ],
                "PrivateDnsName": "ssm.us-west-2.amazonaws.com",
                "ServiceName": "com.amazonaws.us-west-2.ssm",
                "VpcEndpointPolicySupported": true,
                "Owner": "amazon",
                "AvailabilityZones": [
                    "us-west-2a", 
                    "us-west-2b", 
                    "us-west-2c", 
                    "us-west-2d"
                ],
                "AcceptanceRequired": false,
                "BaseEndpointDnsNames": [
                    "ssm.us-west-2.vpce.amazonaws.com"
                ]
            }
        ],
        "ServiceNames": [
            "com.amazonaws.us-west-2.dynamodb",
            "com.amazonaws.us-west-2.ec2",
            "com.amazonaws.us-west-2.ec2messages",
            "com.amazonaws.us-west-2.elasticloadbalancing",
            "com.amazonaws.us-west-2.kinesis-streams",
            "com.amazonaws.us-west-2.s3",
            "com.amazonaws.us-west-2.ssm"
        ]
    }

**Example 2: To describe the details about an endpoint service**

The following ``describe-vpc-endpoint-services`` example lists the details of the Amazon S3 interface endpoint service. ::

    aws ec2 describe-vpc-endpoint-services \
        --filter 'Name=service-type,Values=Interface' Name=service-name,Values=com.amazonaws.us-west-2.s3

Output::

    {
        "ServiceDetails": [
            {
                "ServiceName": "com.amazonaws.us-west-2.s3",
                "ServiceId": "vpce-svc-081d84efcdEXAMPLE",
                "ServiceType": [
                    {
                        "ServiceType": "Interface"
                    }
                ],
                "AvailabilityZones": [
                    "us-west-2a",
                    "us-west-2b",
                    "us-west-2c",
                    "us-west-2d"
                ],
                "Owner": "amazon",
                "BaseEndpointDnsNames": [
                    "s3.us-west-2.vpce.amazonaws.com"
                ],
                "VpcEndpointPolicySupported": true,
                "AcceptanceRequired": false,
                "ManagesVpcEndpoints": false,
                "Tags": []
            }
        ],
        "ServiceNames": [
            "com.amazonaws.us-west-2.s3"
        ]
    }

For more information, see `View available AWS service names <https://docs.aws.amazon.com/vpc/latest/privatelink/aws-services-privatelink-support.html#vpce-view-available-services>`__ in the *AWS PrivateLink User Guide*.
