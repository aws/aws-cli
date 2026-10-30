**To list room memberships**

The following ``list-room-memberships`` example displays a list of the membership details for the specified chat room. ::

    aws chime list-room-memberships \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --room-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "RoomMemberships": [
            {
                "RoomId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Member": {
                    "MemberId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                    "MemberType": "User",
                    "Email": "zhangw@example.com",
                    "FullName": "Zhang Wei",
                    "AccountId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
                },
                "Role": "Member",
                "InvitedBy": "arn:aws:iam::123456789012:user/alejandro",
                "UpdatedTimestamp": "2019-12-02T22:46:58.532Z"
            },
            {
                "RoomId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Member": {
                    "MemberId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                    "MemberType": "User",
                    "Email": "janed@example.com",
                    "FullName": "Jane Doe",
                    "AccountId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
                },
                "Role": "Administrator",
                "InvitedBy": "arn:aws:iam::123456789012:user/alejandro",
                "UpdatedTimestamp": "2019-12-02T22:46:58.532Z"
            }
        ]
    }

For more information, see `Creating a Chat Room <https://docs.aws.amazon.com/chime/latest/ug/chime-chat-room.html>`__ in the *Amazon Chime User Guide*.