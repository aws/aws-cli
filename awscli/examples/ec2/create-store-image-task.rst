**To store an AMI**

The following ``create-store-image-task`` example stores the specified AMI in the specified S3 bucket. ::

    aws ec2 create-store-image-task \
        --image-id ami-1234567890abcdef0 \
        --bucket myamibucket

Output::

    {
        "ObjectKey": "ami-1234567890abcdef0.bin"
    }

For more information, see `Store and restore an AMI <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ami-store-restore.html>`__ in the *Amazon EC2 User Guide*.