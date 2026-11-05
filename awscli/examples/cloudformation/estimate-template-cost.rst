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
        "Url": "http://calculator.s3.amazonaws.com/calc5.html?key=cloudformation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `What is AWS Pricing Calculator? <https://docs.aws.amazon.com/pricing-calculator/latest/userguide/what-is-pricing-calculator.html>`__ in the *AWS Pricing Calculator User Guide*.
