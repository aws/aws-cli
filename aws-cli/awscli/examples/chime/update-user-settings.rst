**To update user settings**

The following ``update-user-settings`` example enables the specified user to make inbound and outbound calls and send and receive SMS messages. ::

    aws chime update-user-settings \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --user-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --user-settings "Telephony={InboundCalling=true,OutboundCalling=true,SMS=true}"

This command produces no output.

For more information, see `Managing phone numbers in Amazon Chime <https://docs.aws.amazon.com/chime/latest/ag/phone-numbers.html>`__ in the *Amazon Chime Administration Guide*.
