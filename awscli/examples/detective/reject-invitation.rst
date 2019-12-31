**To reject an invitation to become a member account in a behavior graph**

The following ``reject-invitation`` example rejects an invitation to become a member account in the specified behavior graph. ::

    aws detective reject-invitation \
        --graph-arn arn:aws:detective:us-east-1:111122223333:graph:123412341234

This command produces no output.

For more information, see `Responding to a Behavior Graph Invitation <https://docs.aws.amazon.com/detective/latest/adminguide/member-invitation-response.html>`__ in the *Amazon Detective Administration Guide*.
