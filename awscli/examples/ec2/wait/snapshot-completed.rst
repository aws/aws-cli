**To wait until a snapshot is completed**

The following ``wait snapshot-completed`` example pauses and resumes running only after it confirms that the specified snapshot is completed. ::

    aws ec2 wait snapshot-completed \
        --snapshot-ids snap-1234567890abcdef0

This command produces no output.

For more information, see `Create Amazon EBS snapshots <https://docs.aws.amazon.com/ebs/latest/userguide/ebs-creating-snapshot.html>`__ in the *Amazon EBS User Guide*.
