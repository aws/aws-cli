**To generate a duration-based stickiness policy for your HTTPS load balancer**

The following ``create-lb-cookie-stickiness-policy`` example generates a stickiness policy with sticky session lifetimes controlled by the specified expiration period. ::

    aws elb create-lb-cookie-stickiness-policy \
        --load-balancer-name my-load-balancer \
        --policy-name my-duration-cookie-policy \
        --cookie-expiration-period 60

This command produces no output.

For more information, see `Configure sticky sessions for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-sticky-sessions.html>`__ in the *Classic Load Balancers User Guide*.
