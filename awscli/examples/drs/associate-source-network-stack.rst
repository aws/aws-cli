**To associate a source network with a CloudFormation stack**

The following ``associate-source-network-stack`` example associates the specified source network with a CloudFormation stack. ::

    aws drs associate-source-network-stack \
        --source-network-id sn-1234567890abcdef0 \
        --cfn-stack-name my-network-stack

Output::

    {
        "job": {
            "arn": "arn:aws:drs:us-west-2:123456789012:job/drsjob-1234567890abcdef0",
            "creationDateTime": "2024-06-15T20:00:00.000Z",
            "jobID": "drsjob-1234567890abcdef0",
            "status": "PENDING",
            "tags": {},
            "type": "LAUNCH"
        }
    }

For more information, see `Source network recovery <https://docs.aws.amazon.com/drs/latest/userguide/source-network-recovery.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
