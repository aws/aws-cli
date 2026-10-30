**To wait until an image exists**

The following ``wait image-exists`` example pauses and resumes running only after it confirms that the specified Amazon Machine Image exists. ::

    aws ec2 wait image-exists \
        --image-ids ami-0abcdef1234567890

This command produces no output.

For more information, see `Amazon Machine Images in Amazon EC2 <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html>`__ in the *Amazon EC2 User Guide*.
