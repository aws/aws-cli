**To list the port mappings for a specific custom routing accelerator destination**

The following ``list-custom-routing-port-mappings-by-destination`` example provides the port mappings for a specific destination EC2 server (at the destination address) for a custom routing accelerator. ::

    aws globalaccelerator list-custom-routing-port-mappings-by-destination \
        --endpoint-id subnet-abcd123example \
        --destination-address 198.51.100.52

Output::

    {
        "DestinationPortMappings": [
            {
                "AcceleratorArn": "arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                    "AcceleratorSocketAddresses": [
                        {
                            "IpAddress": "192.0.2.250",
                            "Port": 65514
                        },
                        {
                            "IpAddress": "192.10.100.99",
                            "Port": 65514
                        }
                    ],
                    "EndpointGroupArn": "arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/0123vxyz/endpoint-group/ab88888example",
                    "EndpointId": "subnet-abcd123example",
                    "EndpointGroupRegion": "us-west-2",
                    "DestinationSocketAddress": {
                        "IpAddress": "198.51.100.52",
                        "Port": 80
                    },
                    "IpAddressType": "IPv4",
                    "DestinationTrafficState": "ALLOW"
            }
        ]
    }

For more information, see `How custom routing accelerators work in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-custom-routing-how-it-works.html>`__ in the *AWS Global Accelerator Developer Guide*.