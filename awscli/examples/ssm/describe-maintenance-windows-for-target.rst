**To list all Maintenance Windows associated with a specific instance**

This example lists the Maintenance Windows which have targets or tasks that the specified instance is asscoiated with.

Command::

  aws ssm describe-maintenance-windows-for-target --targets Key=InstanceIds,Values=i-1234567890EXAMPLE --resource-type INSTANCE

Output::

  {
    "WindowIdentities": [
        {
            "WindowId": "mw-0c5ed765acEXAMPLE",
            "Name": "My-First-Maintenance-Window"
        }
    ]
  }
