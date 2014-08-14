**To describe the attributes of a load balancer**

This example describes the attributes of a specified load balancer.

Command::

  aws elb describe-load-balancer-attributes --load-balancer-name MyHTTPSLoadBalancer

Output::

  {
    "LoadBalancerAttributes": {
	"ConnectionSettings": {
               "IdleTimeout": 30
      },
      "ConnectionDraining": {
        "Enabled": false,
        "Timeout": 300
      },
      "CrossZoneLoadBalancing": {
        "Enabled": true
      },
      "AccessLog": {
        "Enabled": false
      }
    }
  }

