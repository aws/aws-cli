**To enable a VPC for ClassicLink**

The following ``enable-vpc-classic-link`` example enables ``vpc-88888888`` for ClassicLink. ::

    aws ec2 enable-vpc-classic-link \
        --vpc-id vpc-88888888

Output::

    {
        "Return": true
    }
