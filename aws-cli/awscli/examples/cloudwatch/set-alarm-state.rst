**To temporarily change the state of an alarm**

The following ``set-alarm-state`` example temporarily changes the state of an
Amazon CloudWatch alarm named "myalarm" and sets it to the ALARM state for testing purposes. ::

    aws cloudwatch set-alarm-state \
        --alarm-name "myalarm" \
        --state-value ALARM \
        --state-reason "testing purposes"

This command produces no output.

This command returns to the prompt if successful.

For more information, see `Using Amazon CloudWatch alarms <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Alarms.html>`__ in the *Amazon CloudWatch User Guide*.
