**To list the user hierarchy groups in an instance**

The following ``list-user-hierarchy-groups`` example lists the user hierarchy groups in the specified Amazon Connect instance. ::

    aws connect list-user-hierarchy-groups \
        --instance-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 

Output::

    {
        "UserHierarchyGroupSummaryList": [
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/agent-group/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Name": "Example Corporation"
            }
        ]
    }

For more information, see `Set Up Agent Hierarchies <https://docs.aws.amazon.com/connect/latest/adminguide/agent-hierarchy.html>`__ in the *Amazon Connect Administrator Guide*.
