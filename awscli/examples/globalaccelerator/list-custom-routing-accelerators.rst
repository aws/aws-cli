**To list your custom routing accelerators**

The following ``list-custom-routing-accelerators`` example lists the custom routing accelerators in an AWS account. ::

    aws globalaccelerator list-custom-routing-accelerators

Output::

    {
        "Accelerators": [
            {
                "AcceleratorArn": "arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Name": "TestCustomRoutingAccelerator",
                "IpAddressType": "IPV4",
                "Enabled": true,
                "IpSets": [
                    {
                        "IpFamily": "IPv4",
                        "IpAddresses": [
                            "192.0.2.250",
                            "198.51.100.52"
                        ]
                    }
                ],
                "DnsName": "5a5a5a5a5a5a5a5a.awsglobalaccelerator.com",
                "Status": "DEPLOYED",
                "CreatedTime": 1552424416.0,
                "LastModifiedTime": 1569375641.0
            },
            {
                "AcceleratorArn": "arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Name": "ExampleCustomRoutingAccelerator",
                "IpAddressType": "IPV4",
                "Enabled": true,
                "IpSets": [
                    {
                        "IpFamily": "IPv4",
                        "IpAddresses": [
                            "192.0.2.100",
                            "198.51.100.10"
                        ]
                    }
                ],
                "DnsName": "6a6a6a6a6a6a6a.awsglobalaccelerator.com",
                "Status": "DEPLOYED",
                "CreatedTime": 1575585564.0,
                "LastModifiedTime": 1579809243.0
            }
        ]
    }

For more information, see `Custom routing accelerators in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-custom-routing-accelerators.html>`__ in the *AWS Global Accelerator Developer Guide*.