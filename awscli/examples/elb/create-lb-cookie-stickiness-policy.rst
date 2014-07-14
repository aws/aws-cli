**To generate duration-based stickiness policy for your HTTPS load balancer**

This example generates a stickiness-policy with sticky session lifetimes controlled by the specified expiration period.


Command::

    aws elb create-lb-cookie-stickiness-policy --load-balancer-name MyHTTPSLoadBalancer --policy-name MyDurationStickyPolicy --cookie-expiration-period 60

Output::

    {}

