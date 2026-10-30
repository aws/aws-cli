**To create an endpoint group**

The following ``create-endpoint-group`` example creates an endpoint group with one endpoint. ::

    aws globalaccelerator create-endpoint-group \
        --listener-arn arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/0123vxyz \
        --endpoint-group-region us-west-2 \
        --endpoint-configurations EndpointId=i-1234567890abcdef0,Weight=128

Output::

    {
        "EndpointGroup": {
            "TrafficDialPercentage": 100.0, 
            "EndpointDescriptions": [
                {
                    "Weight": 128, 
                    "EndpointId": "i-1234567890abcdef0"
                }
            ], 
            "EndpointGroupArn": "arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/0123vxyz/endpoint-group/098765zyxwvu", 
            "EndpointGroupRegion": "us-west-2"
        }
    }

For more information, see `Endpoint groups in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-endpoint-groups.html>`__ in the *AWS Global Accelerator Developer Guide*.
