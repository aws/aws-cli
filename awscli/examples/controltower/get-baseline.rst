**To get a Control Tower baseline**

The following ``get-baseline`` example gets details of an AWS Control Tower baseline. ::

    aws controltower get-baseline \
        --baseline-identifier arn:aws:controltower:us-east-1::baseline/LN25R72TTG6IGPTQ

Output::

    {
        "arn": "arn:aws:controltower:us-east-1::baseline/LN25R72TTG6IGPTQ",
        "description": "Sets up shared resources for AWS Identity Center, which prepares the AWSControlTowerBaseline to set up Identity Center access for accounts.",
        "name": "IdentityCenterBaseline"
    }

For more information, see `Types of baselines <https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html>`__ in the *AWS Control Tower User Guide*.