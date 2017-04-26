**To list all patch baselines**

This example lists all patch baselines.

Command::

  aws ssm describe-patch-baselines

Output::

  {
    "BaselineIdentities": [
        {
            "BaselineName": "AWS-DefaultPatchBaseline",
            "DefaultBaseline": true,
            "BaselineDescription": "Default Patch Baseline Provided by AWS.",
            "BaselineId": "arn:aws:ssm:us-west-2:812345678901:patchbaseline/pb-04fb4ae6142167966"
        },
        {
            "BaselineName": "Production-Baseline",
            "DefaultBaseline": false,
            "BaselineDescription": "Baseline containing all updates approved for production systems",
            "BaselineId": "pb-045f10b4f382baeda"
        },
        {
            "BaselineName": "Production-Baseline",
            "DefaultBaseline": false,
            "BaselineDescription": "Baseline containing all updates approved for production systems",
            "BaselineId": "pb-0a2f1059b670ebd31"
        }
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
