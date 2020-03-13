**To provision an address range**

The following ``provision-byoip-cidr`` example provisions the specified address range to use with your AWS resources. ::

    aws globalaccelerator provision-byoip-cidr \
        --cidr 203.0.113.25/24 \
        --cidr-authorization-context Message="$text_message",Signature="$signed_message"

Output::

    {
        "ByoipCidr": {
            "Cidr": "203.0.113.25/24",
            "State": "PENDING_PROVISIONING"
        }
    }

For more information, see `Bring Your Own IP Address in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/using-byoip.html>`__ in the *AWS Global Accelerator Developer Guide*.
