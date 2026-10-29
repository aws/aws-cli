**To delete an interconnect**

The following ``delete-interconnect`` example deletes the specified interconnect. ::

    aws directconnect delete-interconnect \
        --interconnect-id dxcon-fgktov66

Output::

    {
        "interconnectState": "deleted"
    }

For more information, see `Direct Connect dedicated and hosted connections <https://docs.aws.amazon.com/directconnect/latest/UserGuide/WorkingWithConnections.html>`__ in the *AWS Direct Connect User Guide*.
