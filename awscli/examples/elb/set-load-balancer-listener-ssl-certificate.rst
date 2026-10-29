**To update the SSL certificate for an HTTPS load balancer**

The following ``set-load-balancer-listener-ssl-certificate`` example replaces the existing SSL certificate for the specified HTTPS load balancer. ::

    aws elb set-load-balancer-listener-ssl-certificate \
        --load-balancer-name my-load-balancer \
        --load-balancer-port 443 \
        --ssl-certificate-id arn:aws:iam::123456789012:server-certificate/new-server-cert

This command produces no output.

For more information, see `Replace the SSL certificate for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-update-ssl-cert.html>`__ in the *Classic Load Balancers Guide*.
