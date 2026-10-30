**To pause running until an instance is deregistered**

The following ``wait instance-deregistered`` example pauses and continues only after it can confirm that the specified instance is deregistered. ::

    aws elb wait instance-deregistered \
        --load-balancer-name my-loadbalancer \
        --instances InstanceId=i-1234567890abcdef0

This command produces no output.

For more information, see `Register instances with your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-deregister-register-instances.html>`__ in the *Classic Load Balancers Guide*.
