**To wait until an instance exists**

The following ``wait instance-exists`` example pauses and resumes running only after it confirms that the specified instance exists. ::

    aws ec2 wait instance-exists \
        --instance-ids i-1234567890abcdef0

This command produces no output.

For more information, see `Amazon EC2 instance state changes <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html>`__ in the *Amazon EC2 User Guide*.
