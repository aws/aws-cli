**To update a Maintenance Window target**

This example updates the name of a Maintenance Window target.

Command::

  aws ssm update-maintenance-window-target --window-id "mw-0c5ed765acEXAMPLE" --window-target-id "57e8344e-fe64-4023-8191-6bf05EXAMPLE" --name "NewName"

Output::

  {
    "Description": "",
    "OwnerInformation": "",
    "WindowTargetId": "57e8344e-fe64-4023-8191-6bf05EXAMPLE",
    "WindowId": "mw-0c5ed765acEXAMPLE",
    "Targets": [
        {
            "Values": [
                "i-1234567890EXAMPLE"
            ],
            "Key": "InstanceIds"
        }
    ],
    "Name": "NewName"
  }
  