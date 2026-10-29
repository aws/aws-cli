**To list the security profiles in an instance**

The following ``list-security-profiles`` example lists the security profiles in the specified Amazon Connect instance. ::

    aws connect list-security-profiles \
        --instance-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 

Output::

    {
        "SecurityProfileSummaryList": [
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/security-profile/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Name": "CallCenterManager"
            },
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/security-profile/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Name": "QualityAnalyst"
            },
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/security-profile/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "Name": "Agent"
            },
            {
                "Id": "12345678-1111-2222-800e-x2y3c4d5fzzzz",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/security-profile/12345678-1111-2222-800e-x2y3c4d5fzzzz",
                "Name": "Admin"
            }
        ]
    }

For more information, see `Assign Permissions: Security Profiles <https://docs.aws.amazon.com/connect/latest/adminguide/connect-security-profiles.html>`__ in the *Amazon Connect Administrator Guide*.
