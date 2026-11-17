**To delete the retention policy of a log group**

The following ``delete-retention-policy`` example removes the retention policy that has previously been applied to a log group named ``my-logs``. ::

    aws logs delete-retention-policy \
        --log-group-name my-logs

This command produces no output.

For more information, see `Working with log groups and log streams <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html>`__ in the *Amazon CloudWatch Logs User Guide*.
