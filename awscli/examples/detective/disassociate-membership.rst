**To resign membership from a behavior graph**

The following ``disassociate-membership`` example removes the AWS account that runs the command from the specified behavior graph. ::

    aws detective disassociate-membership \
         --graph-arn arn:aws:detective:us-east-1:111122223333:graph:123412341234

For more information, see `Removing Your Account from a Behavior Graph <https://docs.aws.amazon.com/detective/latest/adminguide/member-remove-self-from-graph.html>`__ in the *Amazon Detective Administration Guide*.
