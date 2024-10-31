**To Delete a link**

The following ``delete-link`` example deletes a link between a monitoring account sink and a source account. If the command succeeds, no output is returned. ::

    aws oam delete-link \
        --identifier arn:aws:oam:us-east-2:123456789111:link/a1b2c3d4-5678-90ab-cdef-example11111

For more information, see `CloudWatch cross-account observability <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Unified-Cross-Account.html>`__ in the *Amazon CloudWatch User Guide*.