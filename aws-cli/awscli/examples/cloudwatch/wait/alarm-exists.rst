**To wait until an alarm exists**

The following ``wait alarm-exists`` example pauses and resumes running only after it confirms that the specified CloudWatch alarm exists. ::

    aws cloudwatch wait alarm-exists \
        --alarm-names demo

This command produces no output.

For more information, see `Using Amazon CloudWatch alarms <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Alarms.html>`__ in the *Amazon CloudWatch User Guide*.
