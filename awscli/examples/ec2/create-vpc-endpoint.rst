**To create a gateway endpoint**

This example creates a gateway VPC endpoint between VPC ``vpc-1a2b3c4d`` and Amazon S3 in the us-east-1 region, and associates route table ``rtb-11aa22bb`` with the endpoint.

Command::

  aws ec2 create-vpc-endpoint --vpc-id vpc-1a2b3c4d --service-name com.amazonaws.us-east-1.s3 --route-table-ids rtb-11aa22bb

Output::

  {
    "VpcEndpoint": {
    "PolicyDocument": "{\"Version\":\"2008-10-17\",\"Statement\":[{\"Sid\":\"\",\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"*\",\"Resource\":\"*\"}]}", 
    "VpcId": "vpc-1a2b3c4d", 
    "State": "available", 
    "ServiceName": "com.amazonaws.us-east-1.s3", 
    "RouteTableIds": [
      "rtb-11aa22bb"
    ], 
    "VpcEndpointId": "vpce-3ecf2a57", 
    "CreationTimestamp": "2015-05-15T09:40:50Z"
    }
  }

**To create an interface endpoint**

This example creates an interface VPC endpoint between VPC ``vpc-1a2b3c4d`` and Elastic Load Balancing in the us-east-1 region. The endpoint is created in subnet ``subnet-7b16de0c``, and security group ``sg-1a2b3c4d`` is associated with the endpoint network interface.

Command::

  aws ec2 create-vpc-endpoint --vpc-id vpc-1a2b3c4d --vpc-endpoint-type Interface --service-name com.amazonaws.us-east-1.elasticloadbalancing --subnet-id subnet-7b16de0c --security-group-id sg-1a2b3c4d

Output::

  {
    "VpcEndpoint": {
        "PolicyDocument": "{\n  \"Statement\": [\n    {\n      \"Action\": \"*\", \n      \"Effect\": \"Allow\", \n      \"Principal\": \"*\", \n      \"Resource\": \"*\"\n    }\n  ]\n}", 
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
        "VpcEndpointId": "vpce-088d25a4bbf4a7e66", 
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
        ]
    }
  }