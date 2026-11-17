**To validate an AWS CloudFormation template**

The following ``validate-template`` example validates the ``sampletemplate.json`` template. ::

    aws cloudformation validate-template \
        --template-body file://sampletemplate.json

Contents of ``sampletemplate.json``::

    {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "AWS CloudFormation Sample Template S3_Bucket: Sample template showing how to create an S3 bucket. **WARNING** This template creates an S3 bucket. You will be billed for the AWS resources used if you create a stack from this template.",
        "Resources": {
            "S3Bucket": {
                "Type": "AWS::S3::Bucket",
                "DeletionPolicy": "Retain"
            }
        },
        "Outputs": {
            "BucketName": {
                "Value": {
                    "Ref": "S3Bucket"
                },
                "Description": "Name of the sample Amazon S3 bucket."
            }
        }
    }

Output::

    {
        "Description": "AWS CloudFormation Sample Template S3_Bucket: Sample template showing how to create an S3 bucket. **WARNING** This template creates an S3 bucket. You will be billed for the AWS resources used if you create a stack from this template.",
        "Parameters": [],
        "Capabilities": []
    }

For more information, see `Working with CloudFormation templates <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-guide.html>`__ in the *AWS CloudFormation User Guide*.
