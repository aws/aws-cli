**To describe your moving addresses**

The following ``describe-moving-addresses`` example describes all of your moving Elastic IP addresses. ::

    aws ec2 describe-moving-addresses

Output::

    {
        "MovingAddressStatuses": [
            {
                "PublicIp": "198.51.100.0",
                "MoveStatus": "MovingToVpc"
            }
        ]
    }

The following ``describe-moving-addresses`` example describes all addresses that are moving to the EC2-VPC platform. ::

    aws ec2 describe-moving-addresses --filters Name=moving-status,Values=MovingToVpc