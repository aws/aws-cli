**To generate stickiness-policy for your HTTPS load balancer**

This example generates a stickiness-policy that follows the sticky session lifetimes of the application-generated cookie.


Command::

    aws elb create-app-cookie-stickiness-policy --load-balancer-name MyHTTPSLoadBalancer --policy-name MyAppStickyPolicy --cookie-name MyAppCookie

Output::

    {}

