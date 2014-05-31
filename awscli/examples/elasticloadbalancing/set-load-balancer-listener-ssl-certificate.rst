**To update SSL certificate for your HTTPS load balancer**

This example replaces the existing SSL certificate for your HTTPS load balancer.

Command::

      aws elb set-load-balancer-listener-ssl-certificate --load-balancer-name MyHTTPSLoadBalancer --load-balancer-port 443 --ssl-certificate-id arn:aws:iam::012345678901:server-certificate/scert


Output::

    {}

