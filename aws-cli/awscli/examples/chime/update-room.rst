**To update a chat room**

The following ``update-room`` example  modifies the name of the specified chat room. ::

    aws chime update-room \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --room-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --name teamRoom

Output::

    {
        "Room": {
            "RoomId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "Name": "teamRoom",
            "AccountId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "CreatedBy": "arn:aws:iam::123456789012:user/alejandro",
            "CreatedTimestamp": "2019-12-02T22:29:31.549Z",
            "UpdatedTimestamp": "2019-12-02T22:33:19.310Z"
        }
    }

For more information, see `Creating a Chat Room <https://docs.aws.amazon.com/chime/latest/ug/chime-chat-room.html>`__ in the *Amazon Chime User Guide*.