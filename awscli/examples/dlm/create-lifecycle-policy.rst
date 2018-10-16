**To create a lifecycle policy**

The following example creates a lifecycle policy that creates a daily snapshot of volumes with the specified target tags at the specified time. The snapshot has the tags specified by ``TagsToAdd``. If creating a new snapshot exceeds the specified maximum count, the oldest snapshot is deleted.::

  aws dlm create-lifecycle-policy --description "My first policy" --state ENABLED --execution-role-arn arn:aws:iam::12345678910:role/AWSDataLifecycleManagerDefaultRole --policy-details file://policyDetails.json
  
The following is an example of the ``policyDetails.json`` file.::

  {
     "ResourceTypes": [
        "VOLUME"
     ],
     "TargetTags": [
        {
           "Key": "costcenter",
           "Value": "115"
        }
     ],
     "Schedules":[
        {
           "Name": "DailySnapshots",
           "TagsToAdd": [
              {
                 "Key": "type",
                 "Value": "myDailySnapshot"
              }
           ],
           "CreateRule": {
              "Interval": 24,
              "IntervalUnit": "HOURS",
              "Times": [
                 "03:00"
              ]
           },
           "RetainRule": {
              "Count":5
           }
        }
     ]
  }

The following is example output.::

  {
     "PolicyId": "policy-0123456789abcdef0"
  }
