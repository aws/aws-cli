**Example 1: To enable communication over a VPC peering connection from your local ClassicLink connection**

The following ``modify-vpc-peering-connection-options`` example modifies the VPC peering connection options for peering connection ``pcx-aaaabbbb`` to enable a local ClassicLink connection to communicate with the peer VPC. In this example, the owner of the requester VPC modifies the options. ::

    aws ec2 modify-vpc-peering-connection-options \
        --vpc-peering-connection-id pcx-aaaabbbb \
        --requester-peering-connection-options AllowEgressFromLocalClassicLinkToRemoteVpc=true

Output::

    {
        "RequesterPeeringConnectionOptions": {
            "AllowEgressFromLocalClassicLinkToRemoteVpc": true
        }
    }

**Example 2: To enable communication over a VPC peering connection from your local VPC to a remote ClassicLink connection**

The following ``modify-vpc-peering-connection-options`` example modifies the VPC peering connection options for ``pcx-aaaabbbb`` to enable the local VPC to communicate with the ClassicLink connection in the peer VPC. In this example, the owner of the accepter VPC modifies the options. ::

    aws ec2 modify-vpc-peering-connection-options \
        --vpc-peering-connection-id pcx-aaaabbbb \
        --accepter-peering-connection-options AllowEgressFromLocalVpcToRemoteClassicLink=true

Output::

    {
        "AccepterPeeringConnectionOptions": {
            "AllowEgressFromLocalVpcToRemoteClassicLink": true
        }
    }

**Example 3: To enable DNS resolution support for the VPC peering connection**

The following ``modify-vpc-peering-connection-options`` example modifies the VPC peering connection options for ``pcx-aaaabbbb`` to enable the local VPC to resolve public DNS hostnames to private IP addresses when queried from instances in the peer VPC. In this example, the owner of the requester VPC modifies the options. ::

    aws ec2 modify-vpc-peering-connection-options \
        --vpc-peering-connection-id pcx-aaaabbbb \
        --requester-peering-connection-options AllowDnsResolutionFromRemoteVpc=true

Output::

    {
        "RequesterPeeringConnectionOptions": {
            "AllowDnsResolutionFromRemoteVpc": true
        }
    }

For more information, see `Enable DNS resolution for a VPC peering connection <https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-dns.html>`__ in the *Amazon VPC Peering Guide*.
