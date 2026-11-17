**To create a log stream**

The following ``create-log-stream`` example creates a log stream named ``20150601`` in the log group ``my-logs``. ::

    aws logs create-log-stream \
        --log-group-name my-logs \
        --log-stream-name 20150601

This command produces no output.

For more information, see `Working with log groups and log streams <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html>`__ in the *Amazon CloudWatch Logs User Guide*.
