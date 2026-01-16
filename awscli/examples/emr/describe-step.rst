The following command describes a step with the step ID ``s-3LZC0QUT43AM`` in a cluster with the cluster ID ``j-3SD91U2E1L2QX``::

  aws emr describe-step --cluster-id j-3SD91U2E1L2QX --step-id s-3LZC0QUT43AM

Output::

  {
      "Step": {
          "Status": {
              "Timeline": {
                  "EndDateTime": "2015-06-01T19:14:30.481000-0400",
                  "CreationDateTime": "2015-06-01T19:05:26.597000-0400",
                  "StartDateTime": "2015-06-01T19:13:24.959000-0400"
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
