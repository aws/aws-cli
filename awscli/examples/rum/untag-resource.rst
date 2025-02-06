**To remove one or more tags from the specified resource.**

The following ``untag-resource`` example removes one or more tags from the specified resource. ::

    aws rum untag-resource \
        --resource-arn arn:aws:rum:us-west-1:123456789012:appmonitor/MyWebApp \
        --tag-keys Environment

This command produces no output.

For more information, see `CloudWatch RUM <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html>`__ in the *Amazon CloudWatch User Guide*.