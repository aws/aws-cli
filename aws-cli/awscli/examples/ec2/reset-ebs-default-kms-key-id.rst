**To reset your default CMK for EBS encryption**

The following ``reset-ebs-default-kms-key-id`` example resets the default CMK for EBS encryption for your AWS account in the current Region. ::

    aws ec2 reset-ebs-default-kms-key-id

Output::

    {
        "KmsKeyId": "arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Enable Amazon EBS encryption by default <https://docs.aws.amazon.com/ebs/latest/userguide/encryption-by-default.html>`__ in the *Amazon EBS User Guide*.
