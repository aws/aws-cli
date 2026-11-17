**To list endpoint groups for a listener in a custom routing accelerator**

The following ``list-custom-routing-endpoint-groups`` example lists the endpoint groups for a listener in a custom routing accelerator. ::

    aws globalaccelerator list-custom-routing-endpoint-groups \
        --listener-arn arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/abcdef1234

Output::

    {
        "EndpointGroups": [
            {
                "EndpointGroupArn": "arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/abcdef1234/endpoint-group/ab88888example",
                "EndpointGroupRegion": "us-west-2",
                "DestinationDescriptions": [
                    {
                        "FromPort": 80,
                        "ToPort": 80,
                        "Protocols": [
                            "TCP",
                            "UDP"
                        ]
                    }
                ],
                "EndpointDescriptions": [
                    {
                        "EndpointId": "subnet-abcd123example"
                    }
                ]
            }
        ]
    }

For more information, see `Endpoint groups for custom routing accelerators in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-custom-routing-endpoint-groups.html>`__ in the *AWS Global Accelerator Developer Guide*.