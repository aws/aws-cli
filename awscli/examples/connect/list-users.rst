**To list the user hierarchy groups in an instance**

The following ``list-users`` example lists the users in the specified Amazon Connect instance. ::

    aws connect list-users \
        --instance-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 

Output::

    {
        "UserSummaryList": [
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/agent/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Username": "Jane"
            },
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/agent/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Username": "Paulo"
            },
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/agent/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "Username": "JohnD"
            },
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/agent/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "Username": "JohnS"
            }
        ]
    }

For more information, see `Add Users <https://docs.aws.amazon.com/connect/latest/adminguide/user-management.html>`__ in the *Amazon Connect Administrator Guide*.
