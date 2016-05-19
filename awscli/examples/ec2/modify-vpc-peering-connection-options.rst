**To modify requester options for a VPC peering connection**

In this example, for peering connection ``pcx-aaaabbb``, the owner of the requester VPC modifies the VPC peering connection options to enable a local ClassicLink connection to communicate with the peer VPC. You must specify both options for ``--requester-peering-connection-options`` in the command.

Command::

  aws ec2 modify-vpc-peering-connection-options --vpc-peering-connection-id pcx-aaaabbbb --requester-peering-connection-options AllowEgressFromLocalClassicLinkToRemoteVpc=true,AllowEgressFromLocalVpcToRemoteClassicLink=false
  
Output::

  {
    "RequesterPeeringConnectionOptions": {
      "AllowEgressFromLocalVpcToRemoteClassicLink": false, 
      "AllowEgressFromLocalClassicLinkToRemoteVpc": true
    }
  }

**To modify accepter options for a VPC peering connection**

In this example, the owner of the accepter VPC modifies the VPC peering connection options to enable the local VPC to communicate with the ClassicLink connection in the peer VPC. You must specify both options for ``--accepter-peering-connection-options`` in the command.
Command::

  aws ec2 modify-vpc-peering-connection-options --vpc-peering-connection-id pcx-aaaabbbb --accepter-peering-connection-options AllowEgressFromLocalVpcToRemoteClassicLink=true,AllowEgressFromLocalClassicLinkToRemoteVpc=false

Output::

  {
    "AccepterPeeringConnectionOptions": {
      "AllowEgressFromLocalVpcToRemoteClassicLink": true, 
      "AllowEgressFromLocalClassicLinkToRemoteVpc": false
    }
  }