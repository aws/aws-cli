**To update a listener for a custom routing accelerator**

The following ``update-custom-routing-listener`` example updates a listener to change the port range. ::

    aws globalaccelerator update-custom-routing-listener \
        --listener-arn arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/0123vxyz \
        --port-ranges FromPort=10000,ToPort=20000

Output::

    {
        "Listener": {
            "ListenerArn": "arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/0123vxyz",
            "PortRanges": [
                {
                    "FromPort": 10000,
                    "ToPort": 20000
                }
            ]
        }
    }

For more information, see `Listeners for custom routing accelerators in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-custom-routing-listeners.html>`__ in the *AWS Global Accelerator Developer Guide*.