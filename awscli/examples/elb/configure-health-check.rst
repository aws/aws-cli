**To specify health check settings for your back-end EC2 instances**

This example specifies health check settings to use for evaluating the health of your back-end EC2 instances.


Command::

    aws elb configure-health-check --load-balancer-name MyLoadBalancer --health-check Target=HTTP:80/png,Interval=30,UnhealthyThreshold=2,HealthyThreshold=2,Timeout=3

Output::

   {
      "HealthCheck": {
        "HealthyThreshold": 2,
        "Interval": 30,
        "Target": "HTTP:80/png",
        "Timeout": 3,
        "UnhealthyThreshold": 2
    }

