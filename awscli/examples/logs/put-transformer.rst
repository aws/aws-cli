**To create or update a log transformer**

The following ``put-transformer`` example creates or updates a log transformer for a single log group. ::

	aws logs put-transformer \
	   --transformer-config '[{"parseJSON":{}},{"addKeys":{"entries":[{"key":"metadata.transformed_in","value":"CloudWatchLogs"},{"key":"feature","value":"Transformation"}]}},{"trimString":{"withKeys":["status"]}}]' \
	   --log-group-identifier arn:aws:logs:us-east-1:123456789012:log-group:CWLG

This command produces no output.

For more information, see `Amazon CloudWatch Logs <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html>`__ in the *Amazon CloudWatch User Guide*.