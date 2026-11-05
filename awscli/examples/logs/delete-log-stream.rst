**To delete a log stream**

The following ``delete-log-stream`` example deletes a log stream named ``20150531`` from a log group named ``my-logs``. ::

    aws logs delete-log-stream \
        --log-group-name my-logs \
        --log-stream-name 20150531

This command produces no output.

For more information, see `Working with log groups and log streams <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html>`__ in the *Amazon CloudWatch Logs User Guide*.
