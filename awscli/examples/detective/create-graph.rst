**To enable Amazon Detective and create a new behavior graph**

The following ``create-graph`` example enables Detective for the AWS account that runs the command in the Region where the command is run. The command creates a new behavior graph with that account as its master account. ::

    aws detective create-graph

Output::

    {
        "GraphArn": "arn:aws:detective:us-east-1:111122223333:graph:027c7c4610ea4aacaf0b883093cab899"
    }

For more information, see `Enabling Amazon Detective <https://docs.aws.amazon.com/detective/latest/adminguide/detective-enabling.html>`__ in the *Amazon Detective Administration Guide*.
