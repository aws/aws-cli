**To restore an AMI**

The following ``create-restore-image-task`` example restores an AMI from the specified S3 object. ::

    aws ec2 create-restore-image-task \
        --object-key ami-1234567890abcdef0.bin \
        --bucket myamibucket

Output::

    {
        "ImageId": "ami-0eab20fe36f83e1a8"
    }

For more information, see `Store and restore an AMI <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ami-store-restore.html>`__ in the *Amazon EC2 User Guide*.