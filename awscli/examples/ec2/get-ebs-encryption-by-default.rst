**To describe whether EBS encryption by default is enabled**

The following ``get-ebs-encryption-by-default`` example indicates whether EBS encryption by default is enabled for your AWS account in the current Region. ::

    aws ec2 get-ebs-encryption-by-default

Output::

    {
        "EbsEncryptionByDefault": false
    }

The preceding output indicates that EBS encryption by default is disabled.

The following output indicates that EBS encryption by default is enabled. ::

    {
        "EbsEncryptionByDefault": true
    }

For more information, see `Enable Amazon EBS encryption by default <https://docs.aws.amazon.com/ebs/latest/userguide/encryption-by-default.html>`__ in the *Amazon EBS User Guide*.
