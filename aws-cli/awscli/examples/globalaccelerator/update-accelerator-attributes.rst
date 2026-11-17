**To update an accelerator's attributes**

The following ``update-accelerator-attributes`` example updates an accelerator to enable flow logs. You must specify the ``US-West-2 (Oregon)`` Region to create or update accelerator attributes. ::

    aws globalaccelerator update-accelerator-attributes \
        --accelerator-arn arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --flow-logs-enabled \
        --flow-logs-s3-bucket flowlogs-abc \
        --flow-logs-s3-prefix bucketprefix-abc

Output::

    {
        "AcceleratorAttributes": {
            "FlowLogsEnabled": true,
            "FlowLogsS3Bucket": "flowlogs-abc",
            "FlowLogsS3Prefix": "bucketprefix-abc"
        }
    }

For more information, see `Accelerators in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-accelerators.html>`__ in the *AWS Global Accelerator Developer Guide*.