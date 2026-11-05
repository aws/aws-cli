**To describe a traffic mirror target**

The following ``describe-traffic-mirror-targets`` example displays information about the specified traffic mirror target. ::

    aws ec2 describe-traffic-mirror-targets \
        --traffic-mirror-target-ids tmt-0dabe9b0a6EXAMPLE

Output::

    {
        "TrafficMirrorTargets": [
            {
                "TrafficMirrorTargetId": "tmt-0dabe9b0a6EXAMPLE",
                "NetworkLoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/NLB/7cdec873fEXAMPLE",
                "Type": "network-load-balancer",
                "Description": "Example Network Load Balancer target",
                "OwnerId": "123456789012",
                "Tags": []
            }
        ]
    }

For more information, see `View traffic mirror targets and modify target tags <https://docs.aws.amazon.com/vpc/latest/mirroring/modify-traffic-mirroring-targets.html>`__ in the *Amazon VPC Traffic Mirroring Guide*.