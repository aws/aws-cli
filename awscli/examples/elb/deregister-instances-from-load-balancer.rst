**To deregister instance from your load balancer**

This example deregisters an instance from your load balancer.

Command::

      aws elb deregister-instances-from-load-balancer --load-balancer-name MyHTTPSLoadBalancer --instances i-d6f6fae3


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

