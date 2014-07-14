**To modify attributes of your load balancer**

This example modifies attributes of a specified load balancer. The following example uses JSON syntax on a Windows
operating system to specify the attributes. For information about specifying JSON syntax on your operating system, see
`Quoting Strings`_.

Command::

    aws elb modify-load-balancer-attributes --load-balancer-name MyHTTPSLoadBalancer --load-balancer-attributes "{\"CrossZoneLoadBalancing\":{\"Enabled\":true}}

Output::

   {
      "LoadBalancerAttributes": {
        "CrossZoneLoadBalancing": {
            "Enabled": true
          }
      },
      "LoadBalancerName": "MyHTTPSLoadBalancer"
    }

.. _`Quoting Strings`: http://docs.aws.amazon.com/cli/latest/userguide/cli-using-param.html#quoting-strings

