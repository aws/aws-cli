**To estimate template cost**

The following ``estimate-template-cost`` example generates a cost estimate for a template named ``template.yaml`` in the current folder. ::

    aws cloudformation estimate-template-cost \
        --template-body file://template.yaml

Contents of ``template.yaml``::

    AWSTemplateFormatVersion: "2010-09-09"
    Resources:
      MyInstance:
        Type: AWS::EC2::Instance
        Properties:
          ImageId: ami-0abcdef1234567890
          InstanceType: t3.micro

Output::

    {
        "Url": "http://calculator.s3.amazonaws.com/calc5.html?key=cloudformation/7870825a-xmpl-4def-92e7-c4f8dd360cca"
    }
