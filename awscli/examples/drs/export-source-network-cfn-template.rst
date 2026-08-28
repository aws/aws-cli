**To export a source network CloudFormation template**

The following ``export-source-network-cfn-template`` example exports a CloudFormation template for the specified source network. ::

    aws drs export-source-network-cfn-template \
        --source-network-id sn-1234567890abcdef0

Output::

    {
        "s3DestinationUrl": "s3://amzn-s3-demo-bucket/sn-1234567890abcdef0.json"
    }

For more information, see `Source network recovery <https://docs.aws.amazon.com/drs/latest/userguide/source-network-recovery.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
