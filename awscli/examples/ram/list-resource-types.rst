**To list the resource types that are supported by AWS RAM**

The following ``list-resource-types`` example lists all of the resource types currently supported by AWS RAM. ::

    aws ram list-resource-types

Output::

    {
        "resourceTypes": [
            {
                "resourceType": "route53resolver:FirewallRuleGroup",
                "serviceName": "route53resolver"
            },
            {
                "resourceType": "ec2:LocalGatewayRouteTable",
                "serviceName": "ec2"
            },
            {
                "resourceType": "ec2:Subnet",
                "serviceName": "ec2"
            },
            {
                "resourceType": "ec2:TransitGatewayMulticastDomain",
                "serviceName": "ec2"
            }
        ]
    }

For more information, see `Shareable AWS resources <https://docs.aws.amazon.com/ram/latest/userguide/shareable.html>`__ in the *AWS RAM User Guide*.
