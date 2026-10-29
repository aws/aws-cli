**To wait until a volume is deleted**

The following ``wait volume-deleted`` example command pauses and resumes running only after it confirms that the specified volume is deleted. ::

    aws ec2 wait volume-deleted \
        --volume-ids vol-1234567890abcdef0

This command produces no output.
