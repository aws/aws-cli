**To get information about an on-premises instance**

This example gets information about an on-premises instance.

Command::

  aws deploy get-on-premises-instance --instance-name AssetTag12010298EX

Output::

  {
    "instanceInfo": {
      "iamUserArn": "arn:aws:iam::80398EXAMPLE:user/AWS/CodeDeploy/AssetTag12010298EX",
        "tags": [
          {
            "Value": "CodeDeployDemo-OnPrem",
            "Key": "Name"
          }
        ],
        "instanceName": "AssetTag12010298EX",
        "registerTime": 1425579465.228,
        "instanceArn": "arn:aws:codedeploy:us-east-1:80398EXAMPLE:instance/AssetTag12010298EX_4IwLNI2Alh"
    }
  }