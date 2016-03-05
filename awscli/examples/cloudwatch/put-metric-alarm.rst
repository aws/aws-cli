**To send an Amazon Simple Notification Service email message when CPU utilization exceeds 70 percent**

The following example uses the ``put-metric-alarm`` command to send an Amazon Simple Notification Service email message when CPU utilization exceeds 70 percent::

  aws cloudwatch put-metric-alarm --alarm-name cpu-mon --alarm-description "Alarm when CPU exceeds 70 percent" --metric-name CPUUtilization --namespace AWS/EC2 --statistic Average --period 300 --threshold 70 --comparison-operator GreaterThanThreshold  --dimensions "Name=InstanceId,Value=i-12345678" --evaluation-periods 2 --alarm-actions arn:aws:sns:us-east-1:111122223333:MyTopic --unit Percent

This command returns to the prompt if successful. If an alarm with the same name already exists, it will be overwritten by the new alarm.
