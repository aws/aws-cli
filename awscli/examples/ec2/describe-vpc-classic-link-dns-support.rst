**To describe ClassicLink DNS support for your VPCs**

This example describes the ClassicLink DNS support status of all of your VPCs. 

Command::

  aws ec2 describe-vpc-classic-link-dns-support

Output::

  {
    "Vpcs": [
      {
        "VpcId": "vpc-614cc409", 
        "ClassicLinkDnsSupported": true
      }, 
      {
        "VpcId": "vpc-c64bc1a3", 
        "ClassicLinkDnsSupported": false
      }
    ]
  }