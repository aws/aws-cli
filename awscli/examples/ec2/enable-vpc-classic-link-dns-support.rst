**To enable ClassicLink DNS support for a VPC**

The following ``enable-vpc-classic-link-dns-support`` example enables ClassicLink DNS support for ``vpc-88888888``. ::

    aws ec2 enable-vpc-classic-link-dns-support \
        --vpc-id vpc-88888888

Output::

    {
        "Return": true
    }
