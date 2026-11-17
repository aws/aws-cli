**To link (attach) an EC2-Classic instance to a VPC**

The following ``attach-classic-link-vpc`` example links instance i-1234567890abcdef0 to VPC vpc-88888888 through the VPC security group sg-12312312. ::

    aws ec2 attach-classic-link-vpc \
        --instance-id i-1234567890abcdef0 \
        --vpc-id vpc-88888888 \
        --groups sg-12312312

Output::

    {
        "Return": true
    }