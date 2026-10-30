**To wait until an instance terminates**

The following ``wait instance-terminated`` example pauses and resumes running only after it confirms that the specified instance is terminated. ::

    aws ec2 wait instance-terminated \
        --instance-ids i-1234567890abcdef0

This command produces no output.
