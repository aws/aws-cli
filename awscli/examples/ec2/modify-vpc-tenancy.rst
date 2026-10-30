**To modify the tenancy of a VPC**

The following ``modify-vpc-tenancy`` example modifies the tenancy of VPC ``vpc-1a2b3c4d`` to ``default``. ::

    aws ec2 modify-vpc-tenancy \
        --vpc-id vpc-1a2b3c4d \
        --instance-tenancy default

Output::

    {
        "ReturnValue": true
    }