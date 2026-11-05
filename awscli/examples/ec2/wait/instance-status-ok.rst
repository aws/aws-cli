**To wait until the status of an instance is OK**

The following ``wait instance-status-ok`` example pauses and resumes running only after it confirms that the status of the specified instance is OK. ::

    aws ec2 wait instance-status-ok \
        --instance-ids i-1234567890abcdef0

This command produces no output.

For more information, see `Status checks for Amazon EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-system-instance-status-check.html>`__ in the *Amazon EC2 User Guide*.
