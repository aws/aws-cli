**To wait until an instance is stopped**

The following ``wait instance-stopped`` example pauses and resumes running only after it confirms that the specified instance is stopped. ::

    aws ec2 wait instance-stopped \
        --instance-ids i-1234567890abcdef0

This command produces no output.

For more information, see `Stop and start Amazon EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Stop_Start.html>`__ in the *Amazon EC2 User Guide*.
