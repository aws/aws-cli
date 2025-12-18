**To create the stack definition for a stack refactor operation**

The following ``create-stack-refactor`` example creates the stack definition for stack refactoring. ::

    aws cloudformation create-stack-refactor \
        --stack-definitions \
          StackName=Stack1,TemplateBody@=file://template1-updated.yaml \
          StackName=Stack2,TemplateBody@=file://template2-updated.yaml

Output::

    {
        "StackRefactorId": "9c384f70-4e07-4ed7-a65d-fee5eb430841"
    }

For more information, see `Stack refactoring <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stack-refactoring.html>`__ in the *AWS CloudFormation User Guide*.
