**To remove a user as a member of a chat room**

The following ``delete-room-membership`` example removes the specified member from the specified chat room. ::

    aws chime delete-room-membership \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --room-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --member-id a1b2c3d4-5678-90ab-cdef-EXAMPLE33333

This command produces no output.

For more information, see `Creating a Chat Room <https://docs.aws.amazon.com/chime/latest/ug/chime-chat-room.html>`__ in the *Amazon Chime User Guide*.