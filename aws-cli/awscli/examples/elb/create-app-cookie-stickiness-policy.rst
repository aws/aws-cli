**To generate a stickiness policy for your HTTPS load balancer**

The following ``create-app-cookie-stickiness-policy`` example generates a stickiness policy that follows the sticky session lifetimes of the application-generated cookie. ::

    aws elb create-app-cookie-stickiness-policy \
        --load-balancer-name my-load-balancer \
        --policy-name my-app-cookie-policy \
        --cookie-name my-app-cookie

This command produces no output.

For more information, see `Configure sticky sessions for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-sticky-sessions.html>`__ in the *Classic Load Balancers User Guide*.
