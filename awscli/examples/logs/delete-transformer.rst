**To delete the log transformer**

The following ``delete-transformer`` example deletes the log transformer for the specified log group. ::

	aws logs delete-transformer \
        --log-group-identifier arn:aws:logs:us-east-1:123456789012:log-group:CWLG

This command produces no output.

For more information, see `Amazon CloudWatch Logs <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html>`__ in the *Amazon CloudWatch User Guide*.