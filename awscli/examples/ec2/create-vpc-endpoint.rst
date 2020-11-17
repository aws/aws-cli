**Example 1: To create a gateway endpoint**

The following ``create-vpc-endpoint`` example creates a gateway VPC endpoint between VPC ``vpc-1a2b3c4d`` and Amazon S3 in the ``us-east-1`` region, and associates route table ``rtb-11aa22bb`` with the endpoint. ::

    aws ec2 create-vpc-endpoint \
        --vpc-id vpc-1a2b3c4d \
        --service-name com.amazonaws.us-east-1.s3 \
        --route-table-ids rtb-11aa22bb

Output::

    {
        "VpcEndpoint": {
            "PolicyDocument": "{\"Version\":\"2008-10-17\",\"Statement\":[{\"Sid\":\"\",\"Effect\":\"Allow\",\"Principal\":\"\*\",\"Action\":\"\*\",\"Resource\":\"\*\"}]}",
            "VpcId": "vpc-1a2b3c4d",
            "State": "available",
            "ServiceName": "com.amazonaws.us-east-1.s3",
            "RouteTableIds": [
                "rtb-11aa22bb"
            ],
            "VpcEndpointId": "vpc-1a2b3c4d",
            "CreationTimestamp": "2015-05-15T09:40:50Z"
        }
    }

For more information, see `Creating a gateway endpoint <https://docs.aws.amazon.com/vpc/latest/userguide/vpce-gateway.html#create-gateway-endpoint>`__ in the *Amazon VPC User Guide*.

**Example 2: To create an interface endpoint**

The following ``create-vpc-endpoint`` example creates an interface VPC endpoint between VPC ``vpc-1a2b3c4d`` and Elastic Load Balancing in the ``us-east-1`` region. The command creates the endpoint in subnet ``subnet-7b16de0c`` and associates it with security group ``sg-1a2b3c4d``. ::

    aws ec2 create-vpc-endpoint \
        --vpc-id vpc-1a2b3c4d \
        --vpc-endpoint-type Interface \
        --service-name com.amazonaws.us-east-1.elasticloadbalancing \
        --subnet-id subnet-7b16de0c \
        --security-group-id sg-1a2b3c4d

Output::

    {
        "VpcEndpoint": {
            "PolicyDocument": "{\n  \"Statement\": [\n    {\n      \"Action\": \"\*\", \n      \"Effect\": \"Allow\", \n      \"Principal\": \"\*\", \n      \"Resource\": \"\*\"\n    }\n  ]\n}",
            "VpcId": "vpc-1a2b3c4d",
            "NetworkInterfaceIds": [
                "eni-bf8aa46b"
            ],
            "SubnetIds": [
                "subnet-7b16de0c"
            ],
            "PrivateDnsEnabled": true,
            "State": "pending",
            "ServiceName": "com.amazonaws.us-east-1.elasticloadbalancing",
            "RouteTableIds": [],
            "Groups": [
                {
                    "GroupName": "default",
                    "GroupId": "sg-1a2b3c4d"
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

For more information, see `Creating an interface endpoint <https://docs.aws.amazon.com/vpc/latest/userguide/vpce-interface.html#create-interface-endpoint>`__ in the *Amazon VPC User Guide*.

**Example 3: To create a Gateway Load Balancer endpoint**

The following ``create-vpc-endpoint`` example creates a Gateway Load Balancer endpoint between VPC ``vpc-111122223333aabbc`` and and a service that is configured using a Gateway Load Balancer. ::

    aws ec2 create-vpc-endpoint \
        --service-name com.amazonaws.vpce.us-east-1.vpce-svc-123123a1c43abc123 \
        --vpc-endpoint-type GatewayLoadBalancer \
        --vpc-id vpc-111122223333aabbc \
        --subnet-id subnet-0011aabbcc2233445

Output::

    {
        "VpcEndpoint": {
            "VpcEndpointId": "vpce-aabbaabbaabbaabba",
            "VpcEndpointType": "GatewayLoadBalancer",
            "VpcId": "vpc-111122223333aabbc",
            "ServiceName": "com.amazonaws.vpce.us-east-1.vpce-svc-123123a1c43abc123",
            "State": "pending",
            "SubnetIds": [
                "subnet-0011aabbcc2233445"
            ],
            "RequesterManaged": false,
            "NetworkInterfaceIds": [
                "eni-01010120203030405"
            ],
            "CreationTimestamp": "2020-11-11T08:06:03.522Z",
            "OwnerId": "123456789012"
        }
    }

For more information, see `Gateway Load Balancer endpoints <https://docs.aws.amazon.com/vpc/latest/userguide/vpce-gateway-load-balancer.html>`__ in the *Amazon VPC User Guide*.
