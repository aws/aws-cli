**To describe the tags assigned to load balancer**

This example describes the the tags assigned to a load balancer.

Command::

  aws elb describe-tags --load-balancer-name MyTCPLoadBalancer

Output::

{
    "TagDescriptions": [
        {
            "Tags": [                
                {
                    "Value": "digital-media", 
                    "Key": "department"
                }
            ], 
            "LoadBalancerName": "MyTCPLoadBalancer"
        }
    ]
}


