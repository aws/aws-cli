**Example 1: To copy an AMI to another Region**

The following ``copy-image`` example command copies the specified AMI from the ``us-west-2`` Region to the ``us-east-1`` Region and adds a short description. ::

    aws ec2 copy-image \
        --region us-east-1 \
        --source-region us-west-2 \
        --source-image-id ami-066877671789bd71b \
        --description "This is my copied image."

Output::

    {
        "ImageId": "ami-066877671789bd71b"
    }

For more information, see `Copy an AMI <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/CopyingAMIs.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To copy an AMI to another Region and encrypt the backing snapshot**

The following ``copy-image`` command copies the specified AMI from the ``us-west-2`` Region to the current Region and encrypts the backing snapshot using the specified KMS key. ::

    aws ec2 copy-image \
        --source-region us-west-2 \
        --source-image-id snap-066877671789bd71b \
        --encrypted \
        --kms-key-id alias/my-kms-key

Output::

    {
        "ImageId": "ami-066877671789bd71b"
    }

For more information, see `Copy an AMI <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/CopyingAMIs.html>`__ in the *Amazon EC2 User Guide*.