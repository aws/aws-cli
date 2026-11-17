**To associate a security group with a load balancer in a VPC**

The following ``apply-security-groups-to-load-balancer`` example associates a security group with the specified load balancer in a VPC. ::

    aws elb apply-security-groups-to-load-balancer \
        --load-balancer-name my-load-balancer \
        --security-groups sg-fc448899

Output::

    {
        "SecurityGroups": [
            "sg-fc448899"
        ]
    }

For more information, see `Configure security groups for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-vpc-security-groups.html>`__ in the *Classic Load Balancers Guide*.
