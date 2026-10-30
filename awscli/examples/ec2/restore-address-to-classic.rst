**To restore an address to EC2-Classic**

The following ``restore-address-to-classic`` example restores Elastic IP address 198.51.100.0 to the EC2-Classic platform. ::

    aws ec2 restore-address-to-classic --public-ip 198.51.100.0

Output::

    {
        "Status": "MoveInProgress",
        "PublicIp": "198.51.100.0"
    }
