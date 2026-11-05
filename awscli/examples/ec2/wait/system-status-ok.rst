**To wait until the system status is OK**

The following ``wait system-status-ok`` example command pauses and resumes running only after it confirms that the system status of the specified instance is OK. ::

    aws ec2 wait system-status-ok \
        --instance-ids i-1234567890abcdef0

This command produces no output.

For more information, see `Status checks for Amazon EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-system-instance-status-check.html>`__ in the *Amazon EC2 User Guide*.
