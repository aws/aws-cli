**To list your address ranges**

The following ``advertise-byoip-cidr`` example advertises an address range with AWS Global Accelerator that you've provisioned for use with your AWS resources. ::

    aws globalaccelerator list-byoip-cidrs

Output::

    {
        "ByoipCidrs": [
            {
                "Cidr": "198.51.100.0/24",
                "State": "READY"
            }
            {
                "Cidr": "203.0.113.25/24",
                "State": "READY"
            }
        ]
    }

For more information, see `Bring Your Own IP Address in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/using-byoip.html>`__ in the *AWS Global Accelerator Developer Guide*.
