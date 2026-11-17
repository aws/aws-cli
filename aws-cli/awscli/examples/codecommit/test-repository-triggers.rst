**To test triggers in a repository**

The following ``test-repository-triggers`` example tests a trigger named ``MyFirstTrigger`` in an AWS CodeCommit repository named ``MyDemoRepo``. In this example, events in the repository trigger notifications
from an Amazon Simple Notification Service (Amazon SNS) topic. ::

    aws codecommit test-repository-triggers \
        --repository-name MyDemoRepo \
        --triggers name=MyFirstTrigger,destinationArn=arn:aws:sns:us-west-2:123456789012:MyCodeCommitTopic,branches=mainline,preprod,events=all

Output::

    {
        "successfulExecutions": [
            "MyFirstTrigger"
        ],
        "failedExecutions": []
    }

For more information, see `Test triggers for an AWS CodeCommit repository <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-notify-test.html>`__ in the *AWS CodeCommit User Guide*.
