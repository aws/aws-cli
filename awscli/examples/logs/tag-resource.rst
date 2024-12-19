**To Assign one or more tags to the specified CloudWatch Logs resource.**

The following ``tag-resource`` example tags a log group named ``demo-log-group``. If the command succeeds, no output is returned. ::

    aws logs tag-resource \
        --resource-arn arn:aws:logs:us-east-1:123456789:log-group:demo-log-group \
        --tags team=Devops

For more information, see `Working with log groups and log streams <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html>`__ in the *Amazon CloudWatch User Guide*.