**To display patch group registrations**

This example lists the patch group registrations.

Command::

  aws ssm describe-patch-groups

Output::

  {
    "Mappings": [
        {
            "PatchGroup": "Production",
            "BaselineIdentity": {
                "BaselineName": "Production-Baseline",
                "DefaultBaseline": false,
                "BaselineDescription": "Baseline containing all updates approved for production systems",
                "BaselineId": "pb-045f10b4f382baeda"
            }
        }
    ]
  }
