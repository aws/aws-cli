**To create a listener for a custom routing accelerator**

The following ``create-custom-routing-listener`` example creates a listener with a port range from 5000 to 10000 for a custom routing accelerator. ::

    aws globalaccelerator create-custom-routing-listener \
        --accelerator-arn arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --port-ranges FromPort=5000,ToPort=10000

Output::

    {
        "Listener": {
            "PortRanges": [
                {
                    "FromPort": 5000,
                    "ToPort": 10000
                }
            ],
            "ListenerArn": "arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/listener/0123vxyz"
        }
    }

For more information, see `Listeners for custom routing accelerators in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-custom-routing-listeners.html>`__ in the *AWS Global Accelerator Developer Guide*.
