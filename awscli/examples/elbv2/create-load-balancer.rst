**To create an Internet-facing load balancer**

This example creates an Internet-facing load balancer and enables the Availability Zones for the specified subnets.

Command::

  aws elbv2 create-load-balancer --name my-load-balancer --subnets subnet-b7d581c0 subnet-8360a9e7

Output::

  {
    "LoadBalancers": [
        {
            "VpcId": "vpc-3ac0fb5f",
            "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188",
            "State": {
                "Code": "provisioning"
            },
            "DNSName": "my-load-balancer-424835706.us-west-2.elb.amazonaws.com",

            "SecurityGroups": [
                "sg-5943793c"
            ],
            "LoadBalancerName": "my-load-balancer",
            "CreatedTime": "2016-03-25T21:26:12.920Z",
            "Scheme": "internet-facing",
            "Type": "application",
            "CanonicalHostedZoneId": "Z2P70J7EXAMPLE",
            "AvailabilityZones": [
                {
                    "SubnetId": "subnet-8360a9e7",
                    "ZoneName": "us-west-2a"
                },
                {
                    "SubnetId": "subnet-b7d581c0",
                    "ZoneName": "us-west-2b"
                }
            ]
        }
    ]
  }

**To create an internal load balancer**

This example creates an internal load balancer and enables the Availability Zones for the specified subnets.

Command::

  aws elbv2 create-load-balancer --name my-internal-load-balancer --scheme internal --subnets subnet-b7d581c0 subnet-8360a9e7

Output::

  {
    "LoadBalancers": [
        {
            "VpcId": "vpc-3ac0fb5f",
            "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-internal-load-balancer/5b49b8d4303115c2",
            "State": {
                "Code": "provisioning"
            },
            "DNSName": "internal-my-internal-load-balancer-1529930873.us-west-2.elb.amazonaws.com",
            "SecurityGroups": [
                "sg-5943793c"
            ],
            "LoadBalancerName": "my-internal-load-balancer",
            "CreatedTime": "2016-03-25T21:29:48.850Z",
            "Scheme": "internal",
            "Type": "application",
            "CanonicalHostedZoneId": "Z2P70J7EXAMPLE",
            "AvailabilityZones": [
                {
                    "SubnetId": "subnet-8360a9e7",
                    "ZoneName": "us-west-2a"
                },
                {
                    "SubnetId": "subnet-b7d581c0",
                    "ZoneName": "us-west-2b"
                }
            ]
        }
    ]
  }
