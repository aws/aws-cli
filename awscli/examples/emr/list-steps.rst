**To list the steps in a cluster**

The following ``list-steps`` example lists all of the steps in a cluster with the cluster ID ``j-3SD91U2E1L2QX``. ::

    aws emr list-steps \
        --cluster-id j-3SD91U2E1L2QX

Output::

    {
        "Steps": [
            {
                "Id": "s-2BRWVHXA3EXBT",
                "Name": "Custom JAR",
                "Config": {
                    "Jar": "s3://amzn-s3-demo-bucket/mytest.jar",
                    "Properties": {},
                    "MainClass": "mymainclass",
                    "Args": [
                        "arg1",
                        "arg2"
                    ]
                },
                "ActionOnFailure": "CONTINUE",
                "Status": {
                    "State": "COMPLETED",
                    "StateChangeReason": {},
                    "Timeline": {
                        "CreationDateTime": "2024-05-14T18:07:31.123000+00:00",
                        "StartDateTime": "2024-05-14T18:10:45.456000+00:00",
                        "EndDateTime": "2024-05-14T18:12:20.789000+00:00"
                    }
                }
            },
            {
                "Id": "s-1AXF2SNQKPLZR",
                "Name": "Setup Hadoop Debugging",
                "Config": {
                    "Jar": "command-runner.jar",
                    "Properties": {},
                    "Args": [
                        "state-pusher-script"
                    ]
                },
                "ActionOnFailure": "TERMINATE_CLUSTER",
                "Status": {
                    "State": "COMPLETED",
                    "StateChangeReason": {},
                    "Timeline": {
                        "CreationDateTime": "2024-05-14T18:01:02.345000+00:00",
                        "StartDateTime": "2024-05-14T18:09:30.678000+00:00",
                        "EndDateTime": "2024-05-14T18:10:40.901000+00:00"
                    }
                }
            }
        ]
    }

For more information, see `Submit work to an Amazon EMR cluster <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-work-with-steps.html>`__ in the *Amazon EMR Management Guide*.
