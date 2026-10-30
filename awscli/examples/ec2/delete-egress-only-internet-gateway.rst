**To delete an egress-only Internet gateway**

The following ``delete-egress-only-internet-gateway`` example deletes the specified egress-only Internet gateway. ::

    aws ec2 delete-egress-only-internet-gateway \
        --egress-only-internet-gateway-id eigw-01eadbd45ecd7943f

Output::

    {
        "ReturnCode": true
    }

For more information, see `Enable outbound IPv6 traffic using an egress-only internet gateway <https://docs.aws.amazon.com/vpc/latest/userguide/egress-only-internet-gateway.html>`__ in the *Amazon VPC User Guide*.
