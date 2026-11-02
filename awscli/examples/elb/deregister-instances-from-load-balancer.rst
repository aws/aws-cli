**To deregister instances from a load balancer**

The following ``deregister-instances-from-load-balancer`` example deregisters the specified instance from the specified load balancer. ::

    aws elb deregister-instances-from-load-balancer \
        --load-balancer-name my-load-balancer \
        --instances i-d6f6fae3


Output::

    {
        "Instances": [
            {
                "InstanceId": "i-207d9717"
            },
            {
                "InstanceId": "i-afefb49b"
            }
        ]
    }

For more information, see `Register instances with your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-deregister-register-instances.html>`__ in the *Classic Load Balancers User Guide*.
