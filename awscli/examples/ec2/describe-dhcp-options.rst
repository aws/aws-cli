**To describe your DHCP options**

The following ``describe-dhcp-options`` example retrieves details about your DHCP options. ::

    aws ec2 describe-dhcp-options

Output::

    {
        "DhcpOptions": [
            {
                "DhcpConfigurations": [
                    {
                        "Key": "domain-name",
                        "Values": [
                            {
                                "Value": "us-east-2.compute.internal"
                            }
                        ]
                    },
                    {
                        "Key": "domain-name-servers",
                        "Values": [
                            {
                                "Value": "AmazonProvidedDNS"
                            }
                        ]
                    }
                ],
                "DhcpOptionsId": "dopt-19edf471",
                "OwnerId": "111122223333"
            },
            {
                "DhcpConfigurations": [
                    {
                        "Key": "domain-name",
                        "Values": [
                            {
                                "Value": "us-east-2.compute.internal"
                            }
                        ]
                    },
                    {
                        "Key": "domain-name-servers",
                        "Values": [
                            {
                                "Value": "AmazonProvidedDNS"
                            }
                        ]
                    }
                ],
                "DhcpOptionsId": "dopt-fEXAMPLE",
                "OwnerId": "111122223333"
            }
        ]
    } 

For more information, see `Working with DHCP Option Sets <https://docs.aws.amazon.com/vpc/latest/userguide/VPC_DHCP_Options.html#DHCPOptionSet>`__ in the *AWS VPC User Guide*.
