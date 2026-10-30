**To get information about triggers in a repository**

The following ``get-repository-triggers`` example displays details about triggers configured for an AWS CodeCommit repository named ``MyDemoRepo``. ::

    aws codecommit get-repository-triggers \
        --repository-name MyDemoRepo

Output::

    {
        "configurationId": "f7579e13-b83e-4027-aaef-650c0EXAMPLE",
        "triggers": [
            {
                "destinationArn": "arn:aws:sns:us-east-1:111111111111:MyCodeCommitTopic",
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
                "destinationArn": "arn:aws:lambda:us-east-1:111111111111:function:MyCodeCommitPythonFunction",
                "branches": [],
                "name": "MySecondTrigger",
                "customData": "EXAMPLE",
                "events": [
                    "all"
                ]
            }
        ]
    }

For more information, see `Manage triggers for an AWS CodeCommit repository <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-notify.html>`__ in the *AWS CodeCommit User Guide*.
