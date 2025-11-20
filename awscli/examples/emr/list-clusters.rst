The following command lists all active EMR clusters in the current region::

  aws emr list-clusters --active

Output::

  {
      "Clusters": [
          {
              "Status": {
                  "Timeline": {
                      "ReadyDateTime": "2025-10-28T11:11:52.228000-04:00",
                      "CreationDateTime": "2025-10-28T11:02:22.179000-04:00"
                  },
                  "State": "WAITING",
                  "StateChangeReason": {
                      "Message": "Waiting after step completed"
                  }
              },
              "NormalizedInstanceHours": 6,
              "Id": "j-3SD91U2E1L2QX",
              "Name": "my-cluster"
          }
      ]
  }
