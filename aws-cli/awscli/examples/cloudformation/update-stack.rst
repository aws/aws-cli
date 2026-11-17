**To update AWS CloudFormation stacks**

The following ``update-stack`` example updates the template and input parameters for the ``mystack`` stack. ::

    aws cloudformation update-stack \
        --stack-name mystack \
        --template-url https://s3.amazonaws.com/sample/updated.template \
        --parameters ParameterKey=KeyPairName,ParameterValue=SampleKeyPair ParameterKey=SubnetIDs,ParameterValue=SampleSubnetID1\\,SampleSubnetID2

Output::

    {
        "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/mystack/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

The following ``update-stack`` example updates just the ``SubnetIDs`` parameter value for the ``mystack`` stack. If you
don't specify a parameter value, the default value that is specified in the template is used. ::

    aws cloudformation update-stack \
        --stack-name mystack \
        --template-url https://s3.amazonaws.com/sample/updated.template \
        --parameters ParameterKey=KeyPairName,UsePreviousValue=true ParameterKey=SubnetIDs,ParameterValue=SampleSubnetID1\\,UpdatedSampleSubnetID2

Output::

    {
        "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/mystack/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

The following ``update-stack`` example adds two stack notification topics to the ``mystack`` stack. ::

    aws cloudformation update-stack \
        --stack-name mystack \
        --use-previous-template \
        --notification-arns "arn:aws:sns:use-east-1:123456789012:mytopic1" "arn:aws:sns:us-west-2:123456789012:mytopic2"

Output::

    {
        "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/mystack/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `AWS CloudFormation stack updates <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks.html>`__ in the *AWS CloudFormation User Guide*.
