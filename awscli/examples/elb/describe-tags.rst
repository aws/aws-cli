**To describe the tags assigned to a load balancer**

The following ``describe-tags`` example describes the tags assigned to the specified load balancer. ::

    aws elb describe-tags \
        --load-balancer-name my-load-balancer

Output::

    {
        "TagDescriptions": [
            {
                "Tags": [
                    {
                        "Value": "lima",
                        "Key": "project"
                    },
                    {
                        "Value": "digital-media",
                        "Key": "department"
                    }
                ],
                "LoadBalancerName": "my-load-balancer"
            }
        ]
    }

