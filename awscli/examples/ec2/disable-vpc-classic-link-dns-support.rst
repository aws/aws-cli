**To disable ClassicLink DNS support for a VPC**

The following ``disable-vpc-classic-link-dns-support`` example disables ClassicLink DNS support for ``vpc-88888888``. ::

    aws ec2 disable-vpc-classic-link-dns-support \
        --vpc-id vpc-88888888

Output::

    {
        "Return": true
    }
