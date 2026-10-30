**To detect drifted resources**

The following ``detect-stack-drift`` example initiates drift detection for the specified stack. ::

    aws cloudformation detect-stack-drift \
        --stack-name my-stack

Output::

    {
        "StackDriftDetectionId": "1a229160-e4d9-xmpl-ab67-0a4f93df83d4"
    }

You can then use this ID with the ``describe-stack-resource-drifts`` command to describe drifted resources.

For more information, see `Detect drift on an entire CloudFormation stack <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/detect-drift-stack.html>`__ in the *AWS CloudFormation User Guide*.
