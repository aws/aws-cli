**To enable all actions for an alarm**

The following ``enable-alarm-actions`` example enables all actions for the alarm named myalarm. ::

    aws cloudwatch enable-alarm-actions \
        --alarm-names myalarm

This command produces no output.

This command returns to the prompt if successful.

For more information, see `Alarm actions <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarm-actions.html>`__ in the *Amazon CloudWatch User Guide*.
