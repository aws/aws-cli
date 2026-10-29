**To wait until an image exists**

The following ``wait image-exists`` example pauses and resumes running only after it confirms that the specified Amazon Machine Image exists. ::

    aws ec2 wait image-exists \
        --image-ids ami-0abcdef1234567890

This command produces no output.
