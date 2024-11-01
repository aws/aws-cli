**To Assign one or more tags to the specified resource**

The following ``tag-resource`` example assign a tag to the log group ``demo-log-group``.

    aws oam tag-resource \
        --resource-arn arn:aws:logs:us-east-1:123456789:log-group:demo-log-group \
        --tags team=Devops

This command produces no output.

For more information, see `CloudWatch cross-account observability <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Unified-Cross-Account.html>`__ in the *Amazon CloudWatch User Guide*.