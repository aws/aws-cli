**To reject an invitation to become a member account in a behavior graph**

The following ``reject-invitation`` example rejects an invitation to become a member account in the behavior graph arn:aws:detective:us-west-2:123456789012:graph:123412341234. ::

    aws detective reject-invitation \
        --graph-arn arn:aws:detective:us-west-2:123456789012:graph:027c7c4610ea4aacaf0b883093cab899

This command produces no output.

For more information, see `Responding to a behavior graph invitation <https://docs.aws.amazon.com/detective/latest/userguide/member-invitation-response.html>`__ in the *Amazon Detective User Guide*.
