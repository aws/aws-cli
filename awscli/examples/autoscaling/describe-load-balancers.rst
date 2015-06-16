**To describe the load balancers for an Auto Scaling group**

This example returns information about the load balancers for the specified Auto Scaling group::

	aws autoscaling describe-load-balancers --auto-scaling-group-name my-asg

The following is example output for this command::

	{
    "LoadBalancers": [
        {
            "State": "Added",
            "LoadBalancerName": "my-lb"
        }
    ]
	}
