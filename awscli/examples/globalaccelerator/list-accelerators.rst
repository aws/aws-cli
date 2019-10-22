**To list your accelerators** 

The following ``list-accelerators`` example lists the accelerators available in your account. ::

    aws globalaccelerator list-accelerators

Output::

    {
        "Accelerators": [
            {
                "Name": "ExampleAccelerator",
                "Enabled": true,
                "DnsName": "a1234567890abcdef.awsglobalaccelerator.com",
                "CreatedTime": 1542394847.0,
                "LastModifiedTime": 1542394847.0,
                "Status": "DEPLOYED",
                "IpAddressType": "IPV4",
                "IpSets": [
                    {
                        "IpFamily": "IPv4",
                        "IpAddresses": [
                            "192.0.2.250",
                            "192.0.2.52"
                        ]
                    }
                ],
                "AcceleratorArn": "arn:aws:globalaccelerator::123456789012:accelerator/1234abcd-abcd-1234-abcd-1234abcdefgh"
            }
        ]
    }

For more information, see `Accelerators in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-accelerators.html>`__ in the *AWS Global Accelerator Developer Guide*.
