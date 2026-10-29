**To delete a listener from your load balancer**

The following ``delete-load-balancer-listeners`` example deletes the listener for the specified port from the specified load balancer. ::

    aws elb delete-load-balancer-listeners \
        --load-balancer-name my-load-balancer \
        --load-balancer-ports 80

This command produces no output.

For more information, see `Listeners for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-listener-config.html>`__ in the *Classic Load Balancers User Guide*.
