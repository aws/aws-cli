**Example 1: To describe a load balancer**

The following ``describe-load-balancers`` example describes the specified load balancer. ::

    aws elbv2 describe-load-balancers \
        --load-balancer-arns arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188

Output::

    {
        "LoadBalancers": [
            {
                "Type": "application",
                "Scheme": "internet-facing",
                "IpAddressType": "ipv4",
                "VpcId": "vpc-3ac0fb5f",
                "AvailabilityZones": [
                    {
                        "ZoneName": "us-west-2a",
                        "SubnetId": "subnet-8360a9e7"
                    },
                    {
                        "ZoneName": "us-west-2b",
                        "SubnetId": "subnet-b7d581c0"
                    }
                ],
                "CreatedTime": "2016-03-25T21:26:12.920Z",
                "CanonicalHostedZoneId": "Z2P70J7EXAMPLE",
                "DNSName": "my-load-balancer-424835706.us-west-2.elb.amazonaws.com",
                "SecurityGroups": [
                    "sg-5943793c"
                ],
                "LoadBalancerName": "my-load-balancer",
                "State": {
                    "Code": "active"
                },
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188"
            }
        ]
    }

**Example 2: To describe all load balancers**

The following ``describe-load-balancers`` example describes all of your load balancers. ::

    aws elbv2 describe-load-balancers

Output::

    {
        "LoadBalancers": [
            {
                "Type": "application",
                "Scheme": "internet-facing",
                "IpAddressType": "ipv4",
                "VpcId": "vpc-3ac0fb5f",
                "AvailabilityZones": [
                    {
                        "ZoneName": "us-west-2a",
                        "SubnetId": "subnet-8360a9e7"
                    },
                    {
                        "ZoneName": "us-west-2b",
                        "SubnetId": "subnet-b7d581c0"
                    }
                ],
                "CreatedTime": "2016-03-25T21:26:12.920Z",
                "CanonicalHostedZoneId": "Z2P70J7EXAMPLE",
                "DNSName": "my-load-balancer-424835706.us-west-2.elb.amazonaws.com",
                "SecurityGroups": [
                    "sg-5943793c"
                ],
                "LoadBalancerName": "my-load-balancer",
                "State": {
                    "Code": "active"
                },
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188"
            },
            {
                "Type": "network",
                "Scheme": "internet-facing",
                "IpAddressType": "ipv4",
                "VpcId": "vpc-3ac0fb5f",
                "AvailabilityZones": [
                    {
                        "ZoneName": "us-west-2a",
                        "SubnetId": "subnet-8360a9e7"
                    }
                ],
                "CreatedTime": "2017-10-15T22:41:25.657Z",
                "CanonicalHostedZoneId": "Z18D5FSEXAMPLE",
                "DNSName": "my-network-load-balancer-5d1b75f4f1cee11e.elb.us-west-2.amazonaws.com",
                "LoadBalancerName": "my-network-load-balancer",
                "State": {
                    "Code": "active"
                },
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/my-network-load-balancer/5d1b75f4f1cee11e"
            }
        ]
    }

For more information, see `Application Load Balancers <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/application-load-balancers.html>`__ in the *Application Load Balancers Guide*.
