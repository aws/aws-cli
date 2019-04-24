**To list all patch baselines**

This example lists all patch baselines.

Command::

  aws ssm describe-patch-baselines

Output::

  {
    "BaselineIdentities": [
        {
            "BaselineId": "arn:aws:ssm:us-east-1:075727635805:patchbaseline/pb-03e3f588eec25344c",
            "BaselineName": "AWS-CentOSDefaultPatchBaseline",
            "OperatingSystem": "CENTOS",
            "BaselineDescription": "Default Patch Baseline for CentOS Provided by AWS.",
            "DefaultBaseline": true
        },
        {
            "BaselineId": "arn:aws:ssm:us-east-1:075727635805:patchbaseline/pb-07d8884178197b66b",
            "BaselineName": "AWS-SuseDefaultPatchBaseline",
            "OperatingSystem": "SUSE",
            "BaselineDescription": "Default Patch Baseline for Suse Provided by AWS.",
            "DefaultBaseline": true
        },
        ...
    ]
  }


**To list all AWS provided patch baselines**

This example lists all patch baselines provided by AWS.

Command::

  aws ssm describe-patch-baselines --filters "Key=OWNER,Values=[AWS]"
  
**To list all patch baselines you own**

This example lists all patch baselines with you as the owner.

Command::

  aws ssm describe-patch-baselines --filters "Key=OWNER,Values=[Self]"
