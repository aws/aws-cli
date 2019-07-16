**To create a gateway endpoint**

The following ``create-vpc-endpoint`` example creates a gateway VPC endpoint between VPC ``vpc-1a2b3c4d`` and Amazon S3 in the ``us-east-1`` region, and associates route table ``rtb-11aa22bb`` with the endpoint. ::

    aws ec2 create-vpc-endpoint \
        --vpc-id vpc-1EXAMPLE \
        --service-name com.amazonaws.us-east-1.s3 \
        --route-table-ids rtb-1EXAMPLE

Output::

    {
        "VpcEndpoint": {
            "PolicyDocument": "{\"Version\":\"2008-10-17\",\"Statement\":[{\"Sid\":\"\",\"Effect\":\"Allow\",\"Principal\":\"\*\",\"Action\":\"\*\",\"Resource\":\"\*\"}]}",
            "VpcId": "vpc-1EXAMPLE",
            "State": "available",
            "ServiceName": "com.amazonaws.us-east-1.s3",
            "RouteTableIds": [
                "rtb-1EXAMPLE"
            ],
            "VpcEndpointId": "vpce-3EXAMPLE",
            "CreationTimestamp": "2015-05-15T09:40:50Z"
        }
    }

For more information, see `Creating a Gateway Endpoint <https://docs.aws.amazon.com/vpc/latest/userguide/vpce-gateway.html#create-gateway-endpoint>`__ in the *AWS VPC User Guide*.

**To create an interface endpoint**

The following ``create-vpc-endpoint`` example creates an interface VPC endpoint between VPC ``vpc-1a2b3c4d`` and Elastic Load Balancing in the ``us-east-1`` region. The command creates the endpoint in subnet ``subnet-7b16de0c`` and associates it with security group ``sg-1a2b3c4d``. ::

    aws ec2 create-vpc-endpoint \
        --vpc-id vpc-1EXAMPLE \
        --vpc-endpoint-type Interface \
        --service-name com.amazonaws.us-east-1.elasticloadbalancing \
        --subnet-id subnet-7EXAMPLE \
        --security-group-id sg-1EXAMPLE

Output::

    {
        "VpcEndpoint": {
            "PolicyDocument": "{\n  \"Statement\": [\n    {\n      \"Action\": \"\*\", \n      \"Effect\": \"Allow\", \n      \"Principal\": \"\*\", \n      \"Resource\": \"\*\"\n    }\n  ]\n}",
            "VpcId": "vpc-1EXAMPLE",
            "NetworkInterfaceIds": [
                "eni-bf8aa46b"
            ],
            "SubnetIds": [
                "subnet-7EXAMPLE"
            ],
            "PrivateDnsEnabled": true,
            "State": "pending",
            "ServiceName": "com.amazonaws.us-east-1.elasticloadbalancing",
            "RouteTableIds": [],
            "Groups": [
                {
                    "GroupName": "default",
                    "GroupId": "sg-1EXAMPLE"
                }
            ],
            "VpcEndpointId": "vpce-088d25a4bbEXAMPLE",
            "VpcEndpointType": "Interface",
            "CreationTimestamp": "2017-09-05T20:14:41.240Z",
            "DnsEntries": [
                {
                    "HostedZoneId": "Z7HUB22UULQXV",
                    "DnsName": "vpce-088d25a4bbf4a7e66-ks83awe7.elasticloadbalancing.us-east-1.vpce.amazonaws.com"
                },
                {
                    "HostedZoneId": "Z7HUB22UULQXV",
                    "DnsName": "vpce-088d25a4bbf4a7e66-ks83awe7-us-east-1a.elasticloadbalancing.us-east-1.vpce.amazonaws.com"
                },
                {
                    "HostedZoneId": "Z1K56Z6FNPJRR",
                    "DnsName": "elasticloadbalancing.us-east-1.amazonaws.com"
                }
            ],
            "OwnerId": "123456789012"
        }
    }

For more information, see `Creating an Interface Endpoint <https://docs.aws.amazon.com/vpc/latest/userguide/vpce-interface.html#create-interface-endpoint>`__ in the *AWS VPC User Guide*.
