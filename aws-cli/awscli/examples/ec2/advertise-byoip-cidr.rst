**To advertise an address range**

The following ``advertise-byoip-cidr`` example advertises the specified public IPv4 address range. ::

    aws ec2 advertise-byoip-cidr \
        --cidr 203.0.113.25/24

Output::

    {
        "ByoipCidr": {
            "Cidr": "203.0.113.25/24",
            "StatusMessage": "ipv4pool-ec2-1234567890abcdef0",
            "State": "provisioned"
        }
    }

For more information, see `Bring your own IP addresses (BYOIP) to Amazon EC2 <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-byoip.html>`__ in the *Amazon EC2 User Guide*.
