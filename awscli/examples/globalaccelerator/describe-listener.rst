**To describe a listener**

The following ``describe-listener`` example describes a listener. ::

    aws globalaccelerator describe-listener \
        --listener-arn arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/abcdef1234

Output::

    {
        "Listener": {
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
    }

For more information, see `Listeners in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-listeners.html>`__ in the *AWS Global Accelerator Developer Guide*.