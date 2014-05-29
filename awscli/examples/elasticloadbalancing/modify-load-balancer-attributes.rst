**To modify attributes of your load balancer**

This example modifies attributes of a specified load balancer. The following example uses JSON syntax 
on a Windows operating system to specify the attributes.  For information on specifying JSON syntax on 
your operating system, see 

.._'Quoting Strings':http://docs.aws.amazon.com/cli/latest/userguide/cli-using-param.html#quoting-strings

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


