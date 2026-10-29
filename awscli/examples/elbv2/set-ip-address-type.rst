**To set the address type of a load balancer**

The following ``set-ip-address-type`` example sets the address type of the specified load balancer to ``dualstack``. The load balancer subnets must have associated IPv6 CIDR blocks. ::

    aws elbv2 set-ip-address-type \
        --load-balancer-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188 \
        --ip-address-type dualstack

Output::

    {
        "IpAddressType": "dualstack"
    }

For more information, see `Update the IP address types for your Application Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-ip-address-type.html>`__ in the *Application Load Balancers Guide*.
