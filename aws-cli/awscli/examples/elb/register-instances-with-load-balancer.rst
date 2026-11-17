**To register instances with a load balancer**

The following ``register-instances-with-load-balancer`` example registers the specified instance with the specified load balancer. ::

    aws elb register-instances-with-load-balancer \
        --load-balancer-name my-load-balancer \
        --instances i-d6f6fae3

Output::

    {
        "Instances": [
            {
                "InstanceId": "i-d6f6fae3"
            },
            {
                "InstanceId": "i-207d9717"
            },
            {
                "InstanceId": "i-afefb49b"
            }
        ]
    }

For more information, see `Register instances with your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-deregister-register-instances.html>`__ in the *Classic Load Balancers Guide*.
