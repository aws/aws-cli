**To resign membership from a behavior graph**

The following ``disassociate-membership`` example removes the AWS account that runs the command from the behavior graph arn:aws:detective:us-west-2:123456789012:graph:123412341234. ::

    aws detective disassociate-membership \
        --graph-arn arn:aws:detective:us-west-2:123456789012:graph:027c7c4610ea4aacaf0b883093cab899

This command produces no output.

For more information, see `Removing your account from a behavior graph <https://docs.aws.amazon.com/detective/latest/userguide/member-remove-self-from-graph.html>`__ in the *Amazon Detective User Guide*.
