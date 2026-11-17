**To disable Detective and delete the behavior graph**

The following ``delete-graph`` example disables Detective and deletes the specified behavior graph. ::

    aws detective delete-graph \
        --graph-arn arn:aws:detective:us-west-2:123456789012:graph:027c7c4610ea4aacaf0b883093cab899

This command produces no output.

For more information, see `Disabling Amazon Detective <https://docs.aws.amazon.com/detective/latest/userguide/detective-disabling.html>`__ in the *Amazon Detective Administration Guide*.
