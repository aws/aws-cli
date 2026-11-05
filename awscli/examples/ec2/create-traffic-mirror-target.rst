**Example 1: To create a Network Load Balancer traffic mirror target**

The following ``create-traffic-mirror-target`` example creates a  Network Load Balancer traffic mirror target. ::
    
    aws ec2 create-traffic-mirror-target \
        --description 'Example Network Load Balancer Target' \
        --network-load-balancer-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/NLB/7cdec873EXAMPLE

Output::

    {
        "TrafficMirrorTarget": {
            "Type": "network-load-balancer",
            "Tags": [],
            "Description": "Example Network Load Balancer Target",
            "OwnerId": "123456789012",
            "NetworkLoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/NLB/7cdec873EXAMPLE",
            "TrafficMirrorTargetId": "tmt-0dabe9b0a6EXAMPLE"
        },
        "ClientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

**Example 2: To create a network traffic mirror target**

The following ``create-traffic-mirror-target`` example creates a network interface Traffic Mirror target. ::

    aws ec2 create-traffic-mirror-target \
        --description 'Network interface target' \
        --network-interface-id eni-eni-01f6f631eEXAMPLE

Output::

    {
        "ClientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "TrafficMirrorTarget": {
            "Description": "Network interface target",
            "NetworkInterfaceId": "eni-01f6f631eEXAMPLE",
            "TrafficMirrorTargetId": "tmt-02dcdbe2abEXAMPLE",
            "OwnerId": "123456789012",
            "Type": "network-interface",
            "Tags": []
        }
    }

For more information, see `Create a traffic mirror target <https://docs.aws.amazon.com/vpc/latest/mirroring/create-traffic-mirroring-target.html>`__ in the *Traffic Mirroring Guide*.