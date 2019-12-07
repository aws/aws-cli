**To create an endpoint group**

The following ``create-endpoint-group`` example creates an endpoint group. ::

    aws globalaccelerator create-endpoint-group \
        --listener-arn arn:aws:globalaccelerator::123456789012:accelerator/1234abcd-abcd-1234-abcd-1234abcdefgh/listener/0123vxyz \
        --endpoint-group-region us-east-1 \
        --endpoint-configurations EndpointId=eipalloc-eip01234567890abc,Weight=128 \
        --region us-west-2 \
        --idempotencytoken dcba4321-dcba-4321-dcba-dcba4321

Output::

    {
        "EndpointGroup": {
            "TrafficDialPercentage": 100.0,
            "EndpointDescriptions": [
                {
                    "Weight": 128,
                    "EndpointId": "eipalloc-eip01234567890abc"
                }
            ],
            "EndpointGroupArn": "arn:aws:globalaccelerator::123456789012:accelerator/1234abcd-abcd-1234-abcd-1234abcdefgh/listener/0123vxyz/endpoint-group/098765zyxwvu",
            "EndpointGroupRegion": "us-east-1"
        }
    }

For more information, see `Endpoint Groups in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-endpoint-groups.html>`__ in the *AWS Global Accelerator Developer Guide*.
