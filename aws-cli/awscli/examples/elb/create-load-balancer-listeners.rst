**Example 1: To create HTTP listeners for a load balancer**

The following ``create-load-balancer-listeners`` example creates a listener for your load balancer at port 80 using the HTTP protocol. ::

    aws elb create-load-balancer-listeners \
        --load-balancer-name my-load-balancer \
        --listeners "Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80"

This command produces no output.

For more information, see `Listeners for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-listener-config.html>`__ in the *Classic Load Balancers User Guide*.

**Example 2: To create HTTPS listeners for a load balancer**

The following ``create-load-balancer-listeners`` example creates a listener for your load balancer at port 443 using the HTTPS protocol. ::

    aws elb create-load-balancer-listeners \
        --load-balancer-name my-load-balancer \
        --listeners "Protocol=HTTPS,LoadBalancerPort=443,InstanceProtocol=HTTP,InstancePort=80"

This command produces no output.

For more information, see `Configure an HTTPS listener for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-add-or-delete-listeners.html>`__ in the *Classic Load Balancers User Guide*.
