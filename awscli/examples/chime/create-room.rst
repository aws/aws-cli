**To create a chat room**

The following ``create-room`` example creates a chat room for the specified Amazon Chime account. ::

    aws chime create-room \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --name chatRoom

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
