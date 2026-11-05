**To pause running until the specified instance is in service**

The following ``wait instance-in-service`` example pauses and continues only after it can confirm that the specified instance is in service. ::

    aws elb wait instance-in-service \
        --load-balancer-name my-loadbalancer \
        --instances InstanceId=i-1234567890abcdef0

This command produces no output.

For more information, see `Health checks for the instances for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-healthchecks.html>`__ in the *Classic Load Balancers Guide*.
