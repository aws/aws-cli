**Example 1: To describe your DHCP options**

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
                                "Value": "us-west-2.compute.internal"
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
                "OwnerId": "123456789012"
            },
            {
                "DhcpConfigurations": [
                    {
                        "Key": "domain-name",
                        "Values": [
                            {
                                "Value": "us-west-2.compute.internal"
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
                "OwnerId": "123456789012"
            }
        ]
    }

For more information, see `Working with DHCP Option Sets <https://docs.aws.amazon.com/vpc/latest/userguide/DHCPOptionSet.html>`__ in the *AWS VPC User Guide*.

**Example 2: To describe your DHCP options and filter the output**

The following ``describe-dhcp-options`` example describes your DHCP options and uses a filter to return only DHCP options that have ``example.com`` for the domain name server. The example uses the ``--query`` parameter to display only the configuration information and ID in the output. ::

    aws ec2 describe-dhcp-options \
        --filters Name=key,Values=domain-name-servers Name=value,Values=example.com \
        --query "DhcpOptions[*].[DhcpConfigurations,DhcpOptionsId]"

Output::

    [
        [
            [
                {
                    "Key": "domain-name",
                    "Values": [
                        {
                            "Value": "example.com"
                        }
                    ]
                },
                {
                    "Key": "domain-name-servers",
                    "Values": [
                        {
                            "Value": "172.16.16.16"
                        }
                    ]
                }
            ],
            "dopt-001122334455667ab"
        ]
    ]

For more information, see `Working with DHCP Option Sets <https://docs.aws.amazon.com/vpc/latest/userguide/DHCPOptionSet.html>`__ in the *AWS VPC User Guide*.
