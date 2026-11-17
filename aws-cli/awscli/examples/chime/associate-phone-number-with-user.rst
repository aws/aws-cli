**To associate a phone number with a user**

The following ``associate-phone-number-with-user`` example associates the specified phone number with a user. ::

    aws chime associate-phone-number-with-user \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --user-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --e164-phone-number "+12065550100"

This command produces no output.

For more information, see `Assigning Amazon Chime Business Calling phone numbers <https://docs.aws.amazon.com/chime/latest/ag/assign-cbc-numbers.html>`__ in the *Amazon Chime Administration Guide*.
