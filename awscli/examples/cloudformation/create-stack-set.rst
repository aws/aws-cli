**To create a stack set**

The following ``create-stack-set`` example creates a stack set using the specified YAML file temlplate. ``template.yaml`` is an AWS CloudFormation template in the current folder that defines a stack. ::

    aws cloudformation create-stack-set \
        --stack-set-name my-stack-set \
        --template-body file://template.yaml \
        --description "SNS topic"

Contents of ``template.yaml``::

    AWSTemplateFormatVersion: "2010-09-09"
    Description: SNS topic
    Resources:
      MyTopic:
        Type: AWS::SNS::Topic

Output::

    {
        "StackSetId": "my-stack-set:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

To add stack instances to the stack set, use the ``create-stack-instances`` command.

For more information, see `Create CloudFormation StackSets with self-managed permissions <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-getting-started-create-self-managed.html>`__ in the *AWS CloudFormation User Guide*.
