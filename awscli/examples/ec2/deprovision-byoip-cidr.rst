**To remove an IP address range from use**

The following ``deprovision-byoip-cidr`` example removes the specified address range from use with AWS. ::

    aws ec2 deprovision-byoip-cidr \
        --cidr 203.0.113.25/24

Output::

    {
        "ByoipCidr": {
            "Cidr": "203.0.113.25/24",
            "State": "pending-deprovision"
        }
    }

For more information, see `Bring your own IP addresses (BYOIP) to Amazon EC2 <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-byoip.html>`__ in the *Amazon EC2 User Guide*.
