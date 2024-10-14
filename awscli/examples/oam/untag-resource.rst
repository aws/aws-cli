**To Removes one or more tags from the specified resource.**

The following ``untag-resource`` example removes a tag with the key ``team`` from Sink ``arn:aws:oam:us-east-2:123456789012:sink/a1b2c3d4-5678-90ab-cdef-example12345``. If the command succeeds, no output is returned. ::

    aws oam untag-resource \
        --resource-arn arn:aws:oam:us-east-2:123456789012:sink/f3f42f60-f0f2-425c-1234-12347bdd821f \
        --tag-keys team

For more information, see `CloudWatch cross-account observability <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Unified-Cross-Account.html>`__ in the *Amazon CloudWatch User Guide*.