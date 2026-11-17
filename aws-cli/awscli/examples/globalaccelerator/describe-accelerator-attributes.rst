**To describe an accelerator's attributes**

The following ``describe-accelerator-attributes`` example retrieves the attribute details for an accelerator. ::

    aws globalaccelerator describe-accelerator-attributes \
        --accelerator-arn arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "AcceleratorAttributes": {
            "FlowLogsEnabled": true,
            "FlowLogsS3Bucket": "flowlogs-abc",
            "FlowLogsS3Prefix": "bucketprefix-abc"
        }
    }

For more information, see `Accelerators in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-accelerators.html>`__ in the *AWS Global Accelerator Developer Guide*.