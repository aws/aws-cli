**To get information about triggers in a repository**

The following ``get-repository-triggers`` example displays details about triggers configured for an AWS CodeCommit repository named ``MyDemoRepo``. ::

    aws codecommit get-repository-triggers \
        --repository-name MyDemoRepo

Output::

    {
        "configurationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "triggers": [
            {
                "destinationArn": "arn:aws:sns:us-west-2:123456789012:MyCodeCommitTopic",
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

For more information, see `Manage triggers for an AWS CodeCommit repository <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-notify.html>`__ in the *AWS CodeCommit User Guide*.
