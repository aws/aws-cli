**To describe your default CMK for EBS encryption**

The following ``get-ebs-default-kms-key-id`` example describes the default CMK for EBS encryption for your AWS account. ::

    aws ec2 get-ebs-default-kms-key-id

Output::

    {
        "KmsKeyId": "alias/aws/ebs"
    }

The preceding output shows the default CMK for EBS encryption, which is an AWS managed CMK with the alias ``alias/aws/ebs``.

The following output shows a custom CMK for EBS encryption. ::

    {
        "KmsKeyId": "arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Amazon EBS encryption <https://docs.aws.amazon.com/ebs/latest/userguide/ebs-encryption.html>`__ in the *Amazon EBS User Guide*.
