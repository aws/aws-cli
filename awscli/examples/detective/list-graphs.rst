**To view a list of behavior graphs that your account is the administrator for**

The following ``list-graphs`` example retrieves the behavior graphs that the calling account is the administrator for within the current Region. ::

    aws detective list-graphs

Output::

    {
        "GraphList": [ 
            { 
                "Arn": "arn:aws:detective:us-west-2:123456789012:graph:027c7c4610ea4aacaf0b883093cab899",
                "CreatedTime": "2020-01-22T23:35:11+00:00"
            }
        ]
    }

For more information, see `Viewing the list of accounts <https://docs.aws.amazon.com/detective/latest/userguide/accounts-view-list.html>`__ in the *Amazon Detective User Guide*.
