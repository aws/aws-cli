**To describe your DHCP options sets**

This example describes your DHCP options sets.

Command::

  aws ec2 describe-dhcp-options

Output::

  {
      "DhcpOptions": [
          {
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
          },
          {
              "DhcpConfigurations": [
                  {
                      "Values": [
                          "AmazonProvidedDNS"
                      ],
                      "Key": "domain-name-servers"
                  }
              ],
              "DhcpOptionsId": "dopt-7a8b9c2d"
          }
      ]  
  }