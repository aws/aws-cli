**To create a DHCP options set**

This example creates a DHCP options set.

Command::

  aws ec2 create-dhcp-options --dhcp-configuration "Key=domain-name-servers,Values=10.2.5.1,10.2.5.2"

Output::

  {
      "DhcpOptions": {
          "DhcpConfigurations": [
              {
                  "Values": [
                      "10.2.5.2",
                      "10.2.5.1"
                  ],
                  "Key": "domain-name-servers"
              }
          ],
          "DhcpOptionsId": "dopt-d9070ebb"
      }  
  }