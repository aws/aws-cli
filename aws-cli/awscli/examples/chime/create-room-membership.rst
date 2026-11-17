**To create a room membership**

The following ``create-room-membership`` example adds the specified user to the chat room as a chat room member. ::

    aws chime create-room-membership \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --room-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --member-id a1b2c3d4-5678-90ab-cdef-EXAMPLE33333

Output::

    {
        "RoomMembership": {
            "RoomId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "Member": {
                "MemberId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "MemberType": "User",
                "Email": "janed@example.com",
                "FullName": "Jane Doe",
                "AccountId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            },
            "Role": "Member",
            "InvitedBy": "arn:aws:iam::123456789012:user/alejandro",
            "UpdatedTimestamp": "2019-12-02T22:36:41.969Z"
        }
    }

For more information, see `Creating a Chat Room <https://docs.aws.amazon.com/chime/latest/ug/chime-chat-room.html>`__ in the *Amazon Chime User Guide*.