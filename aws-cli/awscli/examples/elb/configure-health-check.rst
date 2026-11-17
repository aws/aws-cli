**To specify the health check settings for your backend EC2 instances**

The following ``configure-health-check`` example specifies the health check settings used to evaluate the health of your backend EC2 instances. ::

    aws elb configure-health-check \
        --load-balancer-name my-load-balancer \
        --health-check Target=HTTP:80/png,Interval=30,UnhealthyThreshold=2,HealthyThreshold=2,Timeout=3

Output::

    {
        "HealthCheck": {
            "HealthyThreshold": 2,
            "Interval": 30,
            "Target": "HTTP:80/png",
            "Timeout": 3,
            "UnhealthyThreshold": 2
        }
    }

For more information, see `Health checks for the instances for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-healthchecks.html>`__ in the *Classic Load Balancers User Guide*.
