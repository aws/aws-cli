**To disable EBS encryption by default**

The following ``disable-ebs-encryption-by-default`` example disables EBS encryption by default for your AWS account in the current Region. ::

    aws ec2 disable-ebs-encryption-by-default

Output::

    {
        "EbsEncryptionByDefault": false
    }

For more information, see `Enable Amazon EBS encryption by default <https://docs.aws.amazon.com/ebs/latest/userguide/encryption-by-default.html>`__ in the *Amazon EBS User Guide*.
