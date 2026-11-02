**To list listeners for custom routing accelerators**

The following ``list-custom-routing-listeners`` example lists the listeners for a custom routing accelerator. ::

    aws globalaccelerator list-custom-routing-listeners \
        --accelerator-arn arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Listeners": [
            {
                "ListenerArn": "arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/abcdef1234",
                "PortRanges": [
                    {
                        "FromPort": 5000,
                        "ToPort": 10000
                    }
                ]
            }
        ]
    }

For more information, see `Listeners for custom routing accelerators in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-custom-routing-listeners.html>`__ in the *AWS Global Accelerator Developer Guide*.