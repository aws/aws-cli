**To create an endpoint group for a custom routing accelerator**

The following ``create-custom-routing-endpoint-group`` example creates an endpoint group for a custom routing accelerator. ::

    aws globalaccelerator create-custom-routing-endpoint-group \
        --listener-arn arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/0123vxyz \
        --endpoint-group-region us-west-2 \
        --destination-configurations "FromPort=80,ToPort=81,Protocols=TCP,UDP"

Output::

    {
        "EndpointGroup": {
            "EndpointGroupArn": "arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/0123vxyz/endpoint-group/4321abcd",
            "EndpointGroupRegion": "us-west-2",
            "DestinationDescriptions": [
                {
                    "FromPort": 80,
                    "ToPort": 81,
                    "Protocols": [
                        "TCP",
                        "UDP"
                    ]
                }
            ],
            "EndpointDescriptions": []
        }
    }

For more information, see `Endpoint groups for custom routing accelerators in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-custom-routing-endpoint-groups.html>`__ in the *AWS Global Accelerator Developer Guide*.