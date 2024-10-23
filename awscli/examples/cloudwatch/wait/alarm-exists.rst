**To wait until an alarm exists**

The following ``wait alarm-exists`` example pauses and resumes running only after it confirms that the specified CloudWatch alarm exists. If the command succeeds, no output is returned. ::

    aws cloudwatch wait alarm-exists \
        --alarm-names demo