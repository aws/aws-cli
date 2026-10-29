**To disable actions for an alarm**

The following ``disable-alarm-actions`` example disables all actions for the alarm named myalarm. ::

    aws cloudwatch disable-alarm-actions \
        --alarm-names myalarm

This command produces no output.

This command returns to the prompt if successful.

For more information, see `Alarm actions <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarm-actions.html>`__ in the *Amazon CloudWatch User Guide*.
