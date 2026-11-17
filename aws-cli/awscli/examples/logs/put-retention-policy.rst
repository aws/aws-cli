**To set the retention policy of a log group**

The following ``put-retention-policy`` example adds a 5 day retention policy to a log group named ``my-logs``. ::

    aws logs put-retention-policy \
        --log-group-name my-logs \
        --retention-in-days 5

This command produces no output.

For more information, see `Working with log groups and log streams <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html>`__ in the *Amazon CloudWatch Logs User Guide*.
