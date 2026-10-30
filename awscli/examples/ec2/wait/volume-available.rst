**To wait until a volume is available**

The following ``wait volume-available`` example command pauses and resumes running only after it confirms that the specified volume is available. ::

    aws ec2 wait volume-available \
        --volume-ids vol-1234567890abcdef0

This command produces no output.

For more information, see `Create an Amazon EBS volume <https://docs.aws.amazon.com/ebs/latest/userguide/ebs-creating-volume.html>`__ in the *Amazon EBS User Guide*.
