**To Assign one or more tags to the specified resource**

The following ``tag-resource`` example tags a sink ``arn:aws:oam:us-east-2:123456789012:sink/a1b2c3d4-5678-90ab-cdef-example12345``. If the command succeeds, no output is returned. ::

    aws oam tag-resource \
        --resource-arn arn:aws:oam:us-east-2:123456789012:sink/a1b2c3d4-5678-90ab-cdef-example12345 \
        --tags team=Devops

For more information, see `CloudWatch cross-account observability <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Unified-Cross-Account.html>`__ in the *Amazon CloudWatch User Guide*.