**To list chat rooms**

The following ``list-rooms`` example displays a list of chat rooms in the specified account. The list is filtered to only those chat rooms that the specified member belongs to. ::

    aws chime list-rooms \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --member-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "Rooms": [
            {
                "RoomId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Name": "teamRoom",
                "AccountId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "CreatedBy": "arn:aws:iam::123456789012:user/alejandro",
                "CreatedTimestamp": "2019-12-02T22:29:31.549Z",
                "UpdatedTimestamp": "2019-12-02T22:33:19.310Z"
            }
        ]
    }

For more information, see `Creating a Chat Room <https://docs.aws.amazon.com/chime/latest/ug/chime-chat-room.html>`__ in the *Amazon Chime User Guide*.