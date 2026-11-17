**To create multiple room memberships**

The following ``batch-create-room-membership`` example adds multiple users to a chat room as chat room members. It also assigns administrator and member roles to the users. ::

    aws chime batch-create-room-membership \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --room-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --membership-item-list "MemberId=a1b2c3d4-5678-90ab-cdef-EXAMPLE33333,Role=Administrator" "MemberId=a1b2c3d4-5678-90ab-cdef-EXAMPLE44444,Role=Member"

Output::

    {
        "Errors": []
    }

For more information, see `Creating a Chat Room <https://docs.aws.amazon.com/chime/latest/ug/chime-chat-room.html>`__ in the *Amazon Chime User Guide*.