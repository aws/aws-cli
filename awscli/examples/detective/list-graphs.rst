**To view a list of behavior graphs that your account is the administrator for**

The following ``list-graphs`` example retrieves the behavior graphs that the calling account is the administrator for within the current Region. ::

    aws detective list-graphs

Output::

    {
        "GraphList": [ 
            { 
                "Arn": "arn:aws:detective:us-east-1:111122223333:graph:123412341234",
                "CreatedTime": "2020-01-22T23:35:11+00:00"
            }
        ]
    }
