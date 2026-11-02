**To create a change set**

The following ``create-change-set`` example creates a change set with the ``CAPABILITY_IAM`` capability. The file ``template.yaml`` is an AWS CloudFormation template in the current folder that defines a stack that includes IAM resources. ::

    aws cloudformation create-change-set \
        --stack-name my-application \
        --change-set-name my-change-set \
        --template-body file://template.yaml \
        --capabilities CAPABILITY_IAM

Contents of ``template.yaml``::

    AWSTemplateFormatVersion: '2010-09-09'
    Description: Stack that includes an IAM role
    Resources:
      MyRole:
        Type: AWS::IAM::Role
        Properties:
          AssumeRolePolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Principal:
                  Service: lambda.amazonaws.com
                Action: sts:AssumeRole
          ManagedPolicyArns:
            - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

Output::

    {
        "Id": "arn:aws:cloudformation:us-west-2:123456789012:changeSet/my-change-set/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/my-application/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Create a change set for a CloudFormation stack <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets-create.html>`__ in the *AWS CloudFormation User Guide*.
