**Example 1: To send an Amazon Simple Notification Service email message when CPU utilization exceeds 70 percent**

The following ``put-metric-alarm`` example sends an Amazon Simple Notification Service email message when CPU utilization exceeds 70 percent. ::

    aws cloudwatch put-metric-alarm \
        --alarm-name cpu-mon \
        --alarm-description "Alarm when CPU exceeds 70 percent" \
        --metric-name CPUUtilization \
        --namespace AWS/EC2 \
        --statistic Average \
        --period 300 \
        --threshold 70 \
        --comparison-operator GreaterThanThreshold \
        --dimensions "Name=InstanceId,Value=i-12345678" \
        --evaluation-periods 2 \
        --alarm-actions arn:aws:sns:us-west-2:123456789012:MyTopic \
        --unit Percent

This command produces no output.

If an alarm with the same name already exists, it will be overwritten by the new alarm.

For more information, see `Create a CPU usage alarm <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/US_AlarmAtThresholdEC2.html>`__ in the *Amazon CloudWatch User Guide*.

**Example 2: To specify multiple dimensions**

The following ``put-metric-alarm`` example illustrates how to specify multiple dimensions. Each dimension is specified as a Name/Value pair, with a comma between the name and the value. Multiple dimensions are separated by a space. ::

    aws cloudwatch put-metric-alarm \
        --alarm-name "Default_Test_Alarm3" \
        --alarm-description "The default example alarm" \
        --namespace "CW EXAMPLE METRICS" \
        --metric-name Default_Test \
        --statistic Average \
        --period 60 \
        --evaluation-periods 3 \
        --threshold 50 \
        --comparison-operator GreaterThanOrEqualToThreshold \
        --dimensions Name=key1,Value=value1 Name=key2,Value=value2

This command produces no output.

For more information, see `Using Amazon CloudWatch alarms <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Alarms.html>`__ in the *Amazon CloudWatch User Guide*.
