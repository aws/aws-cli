**To get the details about a chat room**

The following ``get-room`` example displays details about the specified chat room. ::

    aws chime get-room \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --room-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "Room": {
            "RoomId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "Name": "chatRoom",
            "AccountId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "CreatedBy": "arn:aws:iam::123456789012:user/alejandro",
            "CreatedTimestamp": "2019-12-02T22:29:31.549Z",
            "UpdatedTimestamp": "2019-12-02T22:29:31.549Z"
        }
    }

For more information, see `Creating a Chat Room <https://docs.aws.amazon.com/chime/latest/ug/chime-chat-room.html>`__ in the *Amazon Chime User Guide*.
