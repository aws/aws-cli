**To delete a policy from your load balancer**

The following ``delete-load-balancer-policy`` example deletes the specified policy from the specified load balancer. The policy must not be enabled on any listener. ::

    aws elb delete-load-balancer-policy \
        --load-balancer-name my-load-balancer \
        --policy-name my-duration-cookie-policy

This command produces no output.

For more information, see `Configure sticky sessions for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-sticky-sessions.html>`__ in the *Classic Load Balancers User Guide*.
