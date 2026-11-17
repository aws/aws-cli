**To describe an endpoint group**

The following ``describe-endpoint-group`` example retrieves details about an endpoint group with the following endpoints: an Amazon EC2 instance, an ALB, and an NLB. ::

    aws globalaccelerator describe-endpoint-group \
        --endpoint-group-arn arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222/endpoint-group/ab88888example

Output::

    {
        "EndpointGroup": {
            "TrafficDialPercentage": 100.0,
            "EndpointDescriptions": [
            {
                "Weight": 128,
                "EndpointId": "i-1234567890abcdef0"
            },
            {
                "Weight": 128,
                "EndpointId": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/ALBTesting/alb01234567890xyz"
            },
            {
                "Weight": 128,
                "EndpointId": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/NLBTesting/alb01234567890qrs"
            }
            ],
            "EndpointGroupArn": "arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222/endpoint-group/4321abcd-abcd-4321-abcd-4321abcdefg",
            "EndpointGroupRegion": "us-west-2"
        }
    }

For more information, see `Endpoint groups in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-endpoint-groups.html>`__ in the *AWS Global Accelerator Developer Guide*.