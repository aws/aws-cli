**To withdraw an address range**

The following ``withdraw-byoip-cidr`` example withdraws an address range from AWS Global Accelerator that you've previously advertised for use with your AWS resources. ::

    aws globalaccelerator withdraw-byoip-cidr \
        --cidr 203.0.113.25/24

Output::

    {
        "ByoipCidr": {
            "Cidr": "203.0.113.25/24",
            "State": "PENDING_WITHDRAWING"
        }
    }

For more information, see `Bring Your Own IP Address in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/using-byoip.html>`__ in the *AWS Global Accelerator Developer Guide*.
