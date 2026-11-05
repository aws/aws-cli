**To add or update a trigger in a repository**

The following ``put-repository-triggers`` example updates triggers named ``MyFirstTrigger`` and ``MySecondTrigger`` using an already-created JSON file (here named ``MyTriggers.json``) that contains the structure of all the triggers for a repository named ``MyDemoRepo``. To learn how to get the JSON for existing triggers, see the ``get-repository-triggers`` command. ::

    aws codecommit put-repository-triggers \
        --repository-name MyDemoRepo \
        --triggers file://MyTriggers.json

Contents of ``MyTriggers.json``::

    {
        "repositoryName": "MyDemoRepo", 
        "triggers": [
            {
                "destinationArn": "arn:aws:sns:us-west-2:80398EXAMPLE:MyCodeCommitTopic", 
                "branches": [
                    "main", 
                    "preprod"
                ], 
                "name": "MyFirstTrigger", 
                "customData": "", 
                "events": [
                    "all"
                ]
            },
            {
                "destinationArn": "arn:aws:lambda:us-west-2:123456789012:function:MyCodeCommitPythonFunction", 
                "branches": [], 
                "name": "MySecondTrigger", 
                "customData": "EXAMPLE", 
                "events": [
                    "all"
                ]
            }
        ]
    }

Output::

    {
        "configurationId": "6fa51cd8-35c1-EXAMPLE"
    }

For more information, see `Edit triggers for an AWS CodeCommit repository <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-notify-edit.html>`__ in the *AWS CodeCommit User Guide*.
