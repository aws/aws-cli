**To describe your VPC endpoints**

The following ``describe-vpc-endpoints`` example displays details for all of your endpoints. ::

    aws ec2 describe-vpc-endpoints

Output::

    {
        "VpcEndpoints": [
            {
                "PolicyDocument": "{\"Version\":\"2008-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"*\",\"Resource\":\"*\"}]}",
                "VpcId": "vpc-aabb1122",
                "NetworkInterfaceIds": [],
                "SubnetIds": [],
                "PrivateDnsEnabled": true,
                "State": "available",
                "ServiceName": "com.amazonaws.us-east-1.dynamodb",
                "RouteTableIds": [
                    "rtb-3d560345"
                ],
                "Groups": [],
                "VpcEndpointId": "vpce-032a826a",
                "VpcEndpointType": "Gateway",
                "CreationTimestamp": "2017-09-05T20:41:28Z",
                "DnsEntries": [],
                "OwnerId": "123456789012"
            },
            {
                "PolicyDocument": "{\n  \"Statement\": [\n    {\n      \"Action\": \"*\", \n      \"Effect\": \"Allow\", \n      \"Principal\": \"*\", \n      \"Resource\": \"*\"\n    }\n  ]\n}",
                "VpcId": "vpc-1a2b3c4d",
                "NetworkInterfaceIds": [
                    "eni-2ec2b084",
                    "eni-1b4a65cf"
                ],
                "SubnetIds": [
                    "subnet-d6fcaa8d",
                    "subnet-7b16de0c"
                ],
                "PrivateDnsEnabled": false,
                "State": "available",
                "ServiceName": "com.amazonaws.us-east-1.elasticloadbalancing",
                "RouteTableIds": [],
                "Groups": [
                    {
                        "GroupName": "default",
                        "GroupId": "sg-54e8bf31"
                    }
                ],
                "VpcEndpointId": "vpce-0f89a33420c1931d7",
                "VpcEndpointType": "Interface",
                "CreationTimestamp": "2017-09-05T17:55:27.583Z",
                "DnsEntries": [
                    {
                        "HostedZoneId": "Z7HUB22UULQXV",
                        "DnsName": "vpce-0f89a33420c1931d7-bluzidnv.elasticloadbalancing.us-east-1.vpce.amazonaws.com"
                    },
                    {
                        "HostedZoneId": "Z7HUB22UULQXV",
                        "DnsName": "vpce-0f89a33420c1931d7-bluzidnv-us-east-1b.elasticloadbalancing.us-east-1.vpce.amazonaws.com"
                    },
                    {
                        "HostedZoneId": "Z7HUB22UULQXV",
                        "DnsName": "vpce-0f89a33420c1931d7-bluzidnv-us-east-1a.elasticloadbalancing.us-east-1.vpce.amazonaws.com"
                    }
                ],
                "OwnerId": "123456789012"
            }
        ]
    }

For more information, see `Modifying a Gateway Endpoint <https://docs.aws.amazon.com/vpc/latest/userguide/vpce-gateway.html#modify-gateway-endpoint>`__ in the *AWS VPC User Guide*.
