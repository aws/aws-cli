**To create a user**

The following ``create-user`` example adds a user with the specified attributes to the specified Amazon Connect instance. ::

    aws connect create-user \
        --username Mary \
        --password Pass@Word1 \
        --identity-info FirstName=Mary,LastName=Major \
        --phone-config PhoneType=DESK_PHONE,AutoAccept=true,AfterContactWorkTimeLimit=60,DeskPhoneNumber=+15555551212 \
        --security-profile-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --routing-profile-id a1b2c3d4-5678-90ab-cdef-EXAMPLE33333 \
        --instance-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 

Output::

    {
        "UserId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
        "UserArn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/agent/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
    }

For more information, see `Add Users <https://docs.aws.amazon.com/connect/latest/adminguide/user-management.html>`__ in the *Amazon Connect Administrator Guide*.
