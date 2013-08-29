**To create an AWS CloudFormation stack**

The following ``create-stacks`` command creates a stack with the name ``myteststack`` using the ``sampletemplate.json`` template::

  aws cloudformation create-stack --stack-name myteststack --template-body file:////home//local//test//sampletemplate.json

Output::

  [
      {
          "StackId": "arn:aws:cloudformation:us-west-2:803981987763:stack/myteststack/a69442d0-0b8f-11e3-8b8a-500150b352e0",
          "Description": "AWS CloudFormation Sample Template S3_Bucket: Sample template showing how to create a publicly accessible S3 bucket. **WARNING** This template creates an S3 bucket. You will be billed for the AWS resources used if you create a stack from this template.",
          "Tags": [],
          "Outputs": [
              {
                  "Description": "Name of S3 bucket to hold website content",
                  "OutputKey": "BucketName",
                  "OutputValue": "myteststack-s3bucket-jssofi1zie2w"
              }
          ],
          "StackStatusReason": null,
          "CreationTime": "2013-08-23T01:02:15.422Z",
          "Capabilities": [],
          "StackName": "myteststack",
          "StackStatus": "CREATE_COMPLETE",
          "DisableRollback": false
      }
  ]

For more information, see `Stacks`_ in the *AWS CloudFormation User Guide*.

.. _`Stacks`: http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/concept-stack.html
