**To create a route**

The following ``create-route`` example creates a route for the specified route table. The route matches all IPv4 traffic (``0.0.0.0/0``) and routes it to the specified Internet gateway. ::

    aws ec2 create-route \
        --route-table-id rtb-22574640 \
        --destination-cidr-block 0.0.0.0/0 \
        --gateway-id igw-c0a643a9

Output::

    {
        "Return": true
    }

For more information, see `Configure route tables <https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html>`__ in the *Amazon VPC User Guide*.

The following ``create-route`` example creates a route in route table rtb-g8ff4ea2. The route matches traffic for the IPv4 CIDR block
10.0.0.0/16 and routes it to VPC peering connection, pcx-1a2b3c4d. This route enables traffic to be directed to the peer
VPC in the VPC peering connection. ::

    aws ec2 create-route \
        --route-table-id rtb-g8ff4ea2 \
        --destination-cidr-block 10.0.0.0/16 \
        --vpc-peering-connection-id pcx-1a2b3c4d

Output::

    {
        "Return": true
    }

For more information, see `Update your route tables for a VPC peering connection <https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-routing.html>`__ in the *Amazon VPC Peering Guide*.

The following ``create-route`` example creates a route in the specified route table that matches all IPv6 traffic (``::/0``) and routes it to the specified egress-only Internet gateway. ::

    aws ec2 create-route \
        --route-table-id rtb-dce620b8 \
        --destination-ipv6-cidr-block ::/0 \
        --egress-only-internet-gateway-id eigw-01eadbd45ecd7943f

Output::

    {
        "Return": true
    }

For more information, see `Enable outbound IPv6 traffic using an egress-only internet gateway <https://docs.aws.amazon.com/vpc/latest/userguide/egress-only-internet-gateway.html>`__ in the *Amazon VPC User Guide*.
