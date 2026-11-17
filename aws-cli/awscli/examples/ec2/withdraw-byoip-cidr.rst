**To stop advertising an address range**

The following ``withdraw-byoip-cidr`` example stops advertising the specified address range. ::

    aws ec2 withdraw-byoip-cidr \
        --cidr 203.0.113.25/24

Output::

    {
        "ByoipCidr": {
            "Cidr": "203.0.113.25/24",
            "StatusMessage": "ipv4pool-ec2-1234567890abcdef0",
            "State": "advertised"
        }
    }

For more information, see `Bring your own IP addresses (BYOIP) to Amazon EC2 <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-byoip.html>`__ in the *Amazon EC2 User Guide*.
