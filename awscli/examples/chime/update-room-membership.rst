**To update a room membership**

The following ``update-room-membership`` example modifies the role of the specified chat room member to ``Administrator``. ::

    aws chime update-room-membership \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --room-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --member-id a1b2c3d4-5678-90ab-cdef-EXAMPLE33333 \
        --role Administrator

Output::

    {
        "RoomMembership": {
            "RoomId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "Member": {
                "MemberId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "MemberType": "User",
                "Email": "sofiamartinez@example.com",
                "FullName": "Sofia Martinez",
                "AccountId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            },
            "Role": "Administrator",
            "InvitedBy": "arn:aws:iam::123456789012:user/admin",
            "UpdatedTimestamp": "2019-12-02T22:40:22.931Z"
        }
    }

For more information, see `Creating a Chat Room <https://docs.aws.amazon.com/chime/latest/ug/chime-chat-room.html>`__ in the *Amazon Chime User Guide*.