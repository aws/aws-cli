**To describe a load balancer**

This example describes the specified load balancer.

Command::

  aws elbv2 describe-load-balancers --load-balancer-arns arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188

Output::

  {
    "LoadBalancers": [
        {
            "VpcId": "vpc-3ac0fb5f",
            "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188",
            "State": {
                "Code": "active"
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

**To describe all load balancers**

This example describes all of your load balancers.

Command::

  aws elbv2 describe-load-balancers 
