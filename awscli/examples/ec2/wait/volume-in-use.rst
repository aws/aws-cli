**To wait until a volume is in use**

The following ``wait volume-in-use`` example pauses and resumes running only after it confirms that the specified volume is in use. ::

    aws ec2 wait volume-in-use \
        --volume-ids vol-1234567890abcdef0

This command produces no output.

For more information, see `Attach an Amazon EBS volume to an Amazon EC2 instance <https://docs.aws.amazon.com/ebs/latest/userguide/ebs-attaching-volume.html>`__ in the *Amazon EBS User Guide*.
