**To describe Reserved Instances modifications**

This example command describes all the Reserved Instances modification requests that have been submitted for your account.

Command::

  aws ec2 describe-reserved-instances-modifications

Output::

  {
      "ReservedInstancesModifications": [
          {
              "Status": "fulfilled",
              "ModificationResults": [
                  {
                      "ReservedInstancesId": "93bbbca2-62f1-4d9d-b225-16bada29e6c7",
                      "TargetConfiguration": {
                          "Platform": "EC2-Classic",
                          "AvailabilityZone": "us-west-1c",
                          "InstanceCount": 10
                      }
                  }
              ],
              "EffectiveDate": "2014-05-05T17:00:00.000Z",
              "CreateDate": "2014-05-05T17:52:52.630Z",
              "UpdateDate": "2014-05-05T18:08:06.698Z",
              "ReservedInstancesModificationId": "rimod-d3ed4335-b1d3-4de6-ab31-0f13aaf46687",
              "ReservedInstancesIds": [
                  {
                      "ReservedInstancesId": "b847fa93-e282-4f55-b59a-1342f5bd7c02"
                  }
              ]
          },
          {
              "Status": "processing",
              "ModificationResults": [
                  {
                      "ReservedInstancesId": "1ba8e2e3-aabb-46c3-bcf5-3fe2fda922e6",
                      "TargetConfiguration": {
                          "Platform": "EC2-VPC",
                          "AvailabilityZone": "us-west-1c",
                          "InstanceCount": 5
                      }
                  }
              ],
              "EffectiveDate": "2014-05-05T18:00:00.000Z",
              "CreateDate": "2014-05-05T18:02:04.937Z",
              "UpdateDate": "2014-05-05T18:02:07.578Z",
              "ReservedInstancesModificationId": "rimod-82fa9020-668f-4fb6-945d-61537009d291",
              "ReservedInstancesIds": [
                  {
                      "ReservedInstancesId": "f127bd27-edb7-44c9-a0eb-0d7e09259af0"
                  }
              ]
          }
      ]
  }


