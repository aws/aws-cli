**To delete a log-group level field index policy**

The following ``delete-index-policy`` example deletes a log-group level field index policy that was applied to a single log group. ::

	aws logs delete-index-policy \
        --log-group-identifier arn:aws:logs:us-east-1:123456789012:log-group:CWLG

This command produces no output.

For more information, see `Amazon CloudWatch Logs <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html>`__ in the *Amazon CloudWatch User Guide*.