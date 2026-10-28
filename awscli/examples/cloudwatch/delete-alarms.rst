**To delete an alarm**

The following ``delete-alarms`` example deletes the Amazon CloudWatch alarm
named "myalarm". This command produces no output. ::

    aws cloudwatch delete-alarms \
        --alarm-names myalarm
