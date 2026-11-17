**To update a custom routing accelerator's attributes**

The following ``update-custom-routing-accelerator-attributes`` example updates a custom routing accelerator to enable flow logs. ::

    aws globalaccelerator update-custom-routing-accelerator-attributes \
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

For more information, see `Custom routing accelerators in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/about-custom-routing-accelerators.html>`__ in the *AWS Global Accelerator Developer Guide*.