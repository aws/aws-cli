**To describe a custom routing accelerator's attributes**

The following ``describe-custom-routing-accelerator-attributes`` example describes the attributes for a custom routing accelerator. ::

    aws globalaccelerator describe-custom-routing-accelerator-attributes \
        --accelerator-arn arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "AcceleratorAttributes": {
        "FlowLogsEnabled": false
        }
    }

For more information, see `Custom routing accelerators in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-custom-routing-accelerators.html>`__ in the *AWS Global Accelerator Developer Guide*.