**To disable ClassicLink for a VPC**

The following ``disable-vpc-classic-link`` example disables ClassicLink for ``vpc-88888888``. ::

    aws ec2 disable-vpc-classic-link \
        --vpc-id vpc-88888888

Output::

    {
        "Return": true
    }
