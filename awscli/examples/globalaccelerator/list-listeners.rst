**To list listeners**

The following ``list-listeners`` example lists the listeners for an accelerator. ::

    aws globalaccelerator list-listeners \
        --accelerator-arn arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Listeners": [
            {
                "ListenerArn": "arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/abcdef1234",
                "PortRanges": [
                    {
                        "FromPort": 80,
                        "ToPort": 80
                    }
                ],
                "Protocol": "TCP",
                "ClientAffinity": "NONE"
            }
        ]
    }

For more information, see `Listeners in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-listeners.html>`__ in the *AWS Global Accelerator Developer Guide*.