The following command lists all active EMR clusters in the current region::

  aws emr list-clusters --active

Output::

  {
      "Clusters": [
          {
              "Status": {
                  "Timeline": {
                      "ReadyDateTime": "2015-06-01T23:13:25.353+00:00",
                      "CreationDateTime": "2015-06-01T23:05:26.596+00:00"
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
