**To create a custom routing accelerator**

The following ``create-custom-routing-accelerator`` example creates a custom routing accelerator with the tags ``Name`` and ``Project``. ::

    aws globalaccelerator create-custom-routing-accelerator \
        --name ExampleCustomRoutingAccelerator \
        --tags Key="Name",Value="Example Name" Key="Project",Value="Example Project" \
        --ip-addresses 192.0.2.250 198.51.100.52

Output::

    {
        "Accelerator": {
            "AcceleratorArn": "arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "IpAddressType": "IPV4",
            "Name": "ExampleCustomRoutingAccelerator",
            "Enabled": true,
            "Status": "IN_PROGRESS",
            "IpSets": [
                {
                    "IpAddresses": [
                        "192.0.2.250",
                        "198.51.100.52"
                    ],
                    "IpFamily": "IPv4"
                }
            ],
            "DnsName":"a1234567890abcdef.awsglobalaccelerator.com",
            "CreatedTime": 1542394847.0,
            "LastModifiedTime": 1542394847.0
        }
    }

For more information, see `Custom routing accelerators in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-custom-routing-accelerators.html>`__ in the *AWS Global Accelerator Developer Guide*.
