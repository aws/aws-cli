**To describe the tags assigned to a load balancer**

The following ``describe-tags`` example describes the tags assigned to the specified load balancer. ::

    aws elbv2 describe-tags \
        --resource-arns arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188

Output::

    {
        "TagDescriptions": [
            {
                "ResourceArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188",
                "Tags": [
                    {
                        "Value": "lima",
                        "Key": "project"
                    },
                    {
                        "Value": "digital-media",
                        "Key": "department"
                    }
                ]
            }
        ]
    }

For more information, see `Tag an Application Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-tags.html>`__ in the *Application Load Balancers Guide*.
