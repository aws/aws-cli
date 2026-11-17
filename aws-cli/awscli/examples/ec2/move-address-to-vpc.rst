**To move an address to EC2-VPC**

The following ``move-address-to-vpc`` example moves Elastic IP address 54.123.4.56 to the EC2-VPC platform. ::

    aws ec2 move-address-to-vpc \
        --public-ip 54.123.4.56

Output::

    {
        "Status": "MoveInProgress"
    }

For more information, see `Elastic IP addresses <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html>`__ in the *Amazon EC2 User Guide*.
