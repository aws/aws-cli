**To pause running until a bundle task is completed**

The following ``wait bundle-task-complete`` example pauses and continues only after it can confirm that the specified bundle task is completed. ::

    aws ec2 wait bundle-task-complete \
        --bundle-ids bun-2a4e041c

This command produces no output.

For more information, see `Create an Amazon S3-backed AMI <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/creating-an-ami-instance-store.html>`__ in the *Amazon EC2 User Guide*.
