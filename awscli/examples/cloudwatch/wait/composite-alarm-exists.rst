**To wait until a composite alarm exists**

The following ``wait composite-alarm-exists`` example pauses and resumes running only after it confirms that the specified CloudWatch alarm exists. If the command succeeds, no output is returned. ::

    aws cloudwatch wait composite-alarm-exists \
        --alarm-names demo \
        --alarm-types CompositeAlarm