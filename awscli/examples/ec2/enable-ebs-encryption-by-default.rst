**To enable EBS encryption by default**

The following ``enable-ebs-encryption-by-default`` example enables EBS encryption by default for your AWS account in the current Region. ::

    aws ec2 enable-ebs-encryption-by-default

Output::

    {
        "EbsEncryptionByDefault": true
    }

For more information, see `Enable Amazon EBS encryption by default <https://docs.aws.amazon.com/ebs/latest/userguide/encryption-by-default.html>`__ in the *Amazon EBS User Guide*.
