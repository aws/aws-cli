**To create the stack definition for a stack refactor operation**

The following ``create-stack-refactor`` example creates the stack definition for stack refactoring. ::

    aws cloudformation create-stack-refactor \
        --stack-definitions StackName=Stack1,TemplateBody@=file://template1-updated.yaml StackName=Stack2,TemplateBody@=file://template2-updated.yaml

Contents of ``template1-updated.yaml``::

    AWSTemplateFormatVersion: "2010-09-09"
    Resources:
      MyBucket:
        Type: AWS::S3::Bucket

Contents of ``template2-updated.yaml``::

    AWSTemplateFormatVersion: "2010-09-09"
    Resources:
      MyQueue:
        Type: AWS::SQS::Queue
      MyTopic:
        Type: AWS::SNS::Topic

Output::

    {
        "StackRefactorId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Stack refactoring <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stack-refactoring.html>`__ in the *AWS CloudFormation User Guide*.
