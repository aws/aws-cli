**To pause running until any registered instance is in service**

The following ``wait any-instance-in-service`` example pauses and continues only after it confirms that the specified load balancer has at least one instance in service. ::

    aws elb wait any-instance-in-service \
        --load-balancer-name my-loadbalancer

This command produces no output.

For more information, see `Health checks for the instances for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-healthchecks.html>`__ in the *Classic Load Balancers Guide*.
