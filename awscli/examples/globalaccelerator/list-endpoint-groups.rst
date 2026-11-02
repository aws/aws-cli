**To list endpoint groups**

The following ``list-endpoint-groups`` example lists the endpoint groups for a listener. This listener has two endpoint groups. ::

    aws globalaccelerator list-endpoint-groups \
        --listener-arn arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/abcdef1234

Output::

    {
        "EndpointGroups": [
            {
                "EndpointGroupArn": "arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/abcdef1234/endpoint-group/ab88888example",
                "EndpointGroupRegion": "eu-central-1",
                "EndpointDescriptions": [],
                "TrafficDialPercentage": 100.0,
                "HealthCheckPort": 80,
                "HealthCheckProtocol": "TCP",
                "HealthCheckIntervalSeconds": 30,
                "ThresholdCount": 3
            },
            {
                "EndpointGroupArn": "arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/abcdef1234/endpoint-group/ab99999example",
                "EndpointGroupRegion": "us-west-2",
                "EndpointDescriptions": [],
                "TrafficDialPercentage": 50.0,
                "HealthCheckPort": 80,
                "HealthCheckProtocol": "TCP",
                "HealthCheckIntervalSeconds": 30,
                "ThresholdCount": 3
            }
        ]
    }

For more information, see `Endpoint Groups in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-endpoint-groups.html>`__ in the *AWS Global Accelerator Developer Guide*.