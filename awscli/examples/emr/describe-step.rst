The following command describes a step with the step ID ``s-3LZC0QUT43AM`` in a cluster with the cluster ID ``j-3SD91U2E1L2QX``::

  aws emr describe-step --cluster-id j-3SD91U2E1L2QX --step-id s-3LZC0QUT43AM

Output::

  {
      "Step": {
          "Status": {
              "Timeline": {
                  "EndDateTime": "2015-06-01T23:14:30.481+00:00",
                  "CreationDateTime": "2015-06-01T23:05:26.597+00:00",
                  "StartDateTime": "2015-06-01T23:13:24.959+00:00"
              },
              "State": "COMPLETED",
              "StateChangeReason": {}
          },
          "Config": {
              "Args": [
                  "s3://us-west-2.elasticmapreduce/libs/hive/hive-script",
                  "--base-path",
                  "s3://us-west-2.elasticmapreduce/libs/hive/",
                  "--install-hive",
                  "--hive-versions",
                  "0.13.1"
              ],
              "Jar": "s3://us-west-2.elasticmapreduce/libs/script-runner/script-runner.jar",
              "Properties": {}
          },
          "Id": "s-3LZC0QUT43AM",
          "ActionOnFailure": "TERMINATE_CLUSTER",
          "Name": "Setup hive"
      }
  }
