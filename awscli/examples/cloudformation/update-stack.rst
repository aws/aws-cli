**To update AWS CloudFormation stacks**

The following ``update-stack`` command updates the template and input parameters for the ``MyStack`` stack::

  aws cloudformation update-stack --stack-name MyStack --template-url https://s3.amazonaws.com/sample/updated.template --parameters ParameterKey=KeyPairName,ParameterValue=SampleKeyPair ParameterKey=SubnetIDs,ParameterValue=SampleSubnetID1\\,SampleSubnetID2

The following ``update-stack`` command updates just the ``SubnetIDs`` parameter value for the ``MyStack`` stack. If you
don't specify a parameter value, the default value that is specified in the template is used::

  aws cloudformation update-stack --stack-name MyStack --template-url https://s3.amazonaws.com/sample/updated.template --parameters ParameterKey=KeyPairName,UsePreviousValue=true ParameterKey=SubnetIDs,ParameterValue=SampleSubnetID1\\,UpdatedSampleSubnetID2

The following ``update-stack`` command adds two stack notification topics to the ``MyStack`` stack::

  aws cloudformation update-stack --stack-name MyStack --use-previous-template --notification-arns "arn:aws:sns:use-east-1:123456789012:mytopic1" "arn:aws:sns:us-east-1:123456789012:mytopic2"

For more information, see `Updating Stacks <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks.html>`_ in the `AWS CloudFormation User Guide <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html>`_.
