- Command::

    aws emr describe-cluster --cluster-id j-XXXXXXXX

- Output::

	For release-label based uniform instance groups cluster:
	
		{
		    "Cluster": {
		        "Status": {
		            "Timeline": {
		                "ReadyDateTime": "2015-07-09T16:51:15.199000-0400", 
		                "CreationDateTime": "2015-07-09T16:44:16.563000-0400"
		            }, 
		            "State": "WAITING",
		            "StateChangeReason": {
		                "Message": "Waiting for steps to run" 
		            }
		        }, 
		        "Ec2InstanceAttributes": {
		            "ServiceAccessSecurityGroup": "sg-xxxxxxxx",
		            "EmrManagedMasterSecurityGroup": "sg-xxxxxxxx", 
		            "IamInstanceProfile": "EMR_EC2_DefaultRole", 
		            "Ec2KeyName": "myKey", 
		            "Ec2AvailabilityZone": "us-east-1c", 
		            "EmrManagedSlaveSecurityGroup": "sg-yyyyyyyyy"
		        }, 
		        "Name": "My Cluster", 
		        "ServiceRole": "EMR_DefaultRole", 
		        "Tags": [], 
		        "TerminationProtected": true, 
		        "UnhealthyNodeReplacement": true, 
		        "ReleaseLabel": "emr-4.0.0", 
		        "NormalizedInstanceHours": 96, 
		        "InstanceGroups": [
		            {
		                "RequestedInstanceCount": 2, 
		                "Status": {
		                    "Timeline": {
		                        "ReadyDateTime": "2015-07-09T16:51:14.245000-0400",
		                        "CreationDateTime": "2015-07-09T16:44:16.564000-0400", 
		                        "EndDateTime": "2015-07-11T14:09:18.387000-0400"
		                    }, 
		                    "State": "RUNNING", 
		                    "StateChangeReason": {
		                        "Message": "", 
		                    }
		                }, 
		                "Name": "CORE", 
		                "InstanceGroupType": "CORE", 
		                "Id": "ig-YYYYYYY", 
		                "Configurations": [], 
		                "InstanceType": "m3.large", 
		                "Market": "ON_DEMAND", 
		                "RunningInstanceCount": 2
		            },
		            {
		                "RequestedInstanceCount": 1, 
		                "Status": {
		                    "Timeline": {
		                        "ReadyDateTime": "2015-07-09T16:51:14.245000-0400", 
		                        "CreationDateTime": "2015-07-09T16:44:16.564000-0400", 
		                        "EndDateTime": "2015-07-11T14:09:18.387000-0400"
		                    }, 
		                    "State": "RUNNING", 
		                    "StateChangeReason": {
		                        "Message": "", 
		                    }
		                }, 
		                "Name": "MASTER", 
		                "InstanceGroupType": "MASTER", 
		                "Id": "ig-XXXXXXXXX", 
		                "Configurations": [], 
		                "InstanceType": "m3.large", 
		                "Market": "ON_DEMAND", 
		                "RunningInstanceCount": 1
		            }
		        ], 
		        "Applications": [
		            {
		                "Name": "Hadoop"
		            }
		        ], 
		        "VisibleToAllUsers": true, 
		        "BootstrapActions": [], 
		        "MasterPublicDnsName": "ec2-54-147-144-78.compute-1.amazonaws.com", 
		        "AutoTerminate": false, 
		        "Id": "j-XXXXXXXX", 
		        "Configurations": [
		            {
		                "Properties": {
		                    "fs.s3.consistent.retryPeriodSeconds": "20", 
		                    "fs.s3.enableServerSideEncryption": "true", 
		                    "fs.s3.consistent": "false", 
		                    "fs.s3.consistent.retryCount": "2"
		                }, 
		                "Classification": "emrfs-site"
		            }
		        ]
		    }
		}


	For release-label based instance fleet cluster:
        {
            "Cluster": {
                "Status": {
                    "Timeline": {
                        "ReadyDateTime": "2017-02-23T19:48:09.705000-0500",
                        "CreationDateTime": "2017-02-23T19:42:13.942000-0500"
                    },
                    "State": "WAITING",
                    "StateChangeReason": {
                        "Message": "Waiting for steps to run"
                    }
                },
                "Ec2InstanceAttributes": {
                    "EmrManagedMasterSecurityGroup": "sg-xxxxx",
                    "RequestedEc2AvailabilityZones": [],
                    "RequestedEc2SubnetIds": [],
                    "IamInstanceProfile": "EMR_EC2_DefaultRole",
                    "Ec2AvailabilityZone": "us-east-1a",
                    "EmrManagedSlaveSecurityGroup": "sg-xxxxx"
                },
                "Name": "My Cluster",
                "ServiceRole": "EMR_DefaultRole",
                "Tags": [],
                "TerminationProtected": false,
                "UnhealthyNodeReplacement": false, 
                "ReleaseLabel": "emr-5.2.0",
                "NormalizedInstanceHours": 472,
                "InstanceCollectionType": "INSTANCE_FLEET",
                "InstanceFleets": [
                    {
                        "Status": {
                            "Timeline": {
                                "ReadyDateTime": "2017-02-23T19:46:52.740000-0500",
                                "CreationDateTime": "2017-02-23T19:42:13.948000-0500"
                            },
                            "State": "RUNNING",
                            "StateChangeReason": {
                                "Message": ""
                            }
                        },
                        "ProvisionedSpotCapacity": 1,
                        "Name": "MASTER",
                        "InstanceFleetType": "MASTER",
                        "LaunchSpecifications": {
                            "SpotSpecification": {
                                "TimeoutDurationMinutes": 60,
                                "TimeoutAction": "TERMINATE_CLUSTER"
                            }
                        },
                        "TargetSpotCapacity": 1,
                        "ProvisionedOnDemandCapacity": 0,
                        "InstanceTypeSpecifications": [
                            {
                                "BidPrice": "0.5",
                                "InstanceType": "m3.xlarge",
                                "WeightedCapacity": 1
                            }
                        ],
                        "Id": "if-xxxxxxx",
                        "TargetOnDemandCapacity": 0
                    }
                ],
                "Applications": [
                    {
                        "Version": "2.7.3",
                        "Name": "Hadoop"
                    }
                ],
                "ScaleDownBehavior": "TERMINATE_AT_INSTANCE_HOUR",
                "VisibleToAllUsers": true,
                "BootstrapActions": [],
                "MasterPublicDnsName": "ec2-xxx-xx-xxx-xx.compute-1.amazonaws.com",
                "AutoTerminate": false,
                "Id": "j-xxxxx",
                "Configurations": []
            }
        }
 
	For ami based uniform instance group cluster:
	
	    {
	        "Cluster": {
	            "Status": {
	                "Timeline": {
	                    "ReadyDateTime": "2014-05-06T14:22:44.432000-0400",
	                    "CreationDateTime": "2014-05-06T14:17:48.62000-0400"
	                },
	                "State": "WAITING",
	                "StateChangeReason": {
	                    "Message": "Waiting for steps to run"
	                }
	            },
	            "Ec2InstanceAttributes": {
	                "IamInstanceProfile": "EMR_EC2_DefaultRole",
	                "Ec2AvailabilityZone": "us-east-1c"
	            },
	            "Name": "My Cluster",
	            "Tags": [],
	            "TerminationProtected": true,
	            "UnhealthyNodeReplacement": true, 
	            "RunningAmiVersion": "2.5.4",
	            "InstanceGroups": [
	                {
	                    "RequestedInstanceCount": 1,
	                    "Status": {
	                        "Timeline": {
	                            "ReadyDateTime": "2014-05-06T14:22:38.848000-0400",
	                            "CreationDateTime": "2014-05-06T14:17:48.621000-0400"
	                        },
	                        "State": "RUNNING",
	                        "StateChangeReason": {
	                            "Message": ""
	                        }
	                    },
	                    "Name": "Master instance group",
	                    "InstanceGroupType": "MASTER",
	                    "InstanceType": "m1.small",
	                    "Id": "ig-ABCD",
	                    "Market": "ON_DEMAND",
	                    "RunningInstanceCount": 1
	                },
	                {
	                    "RequestedInstanceCount": 2,
	                    "Status": {
	                        "Timeline": {
	                            "ReadyDateTime": "2014-05-06T14:22:44.439000-0400",
	                            "CreationDateTime": "2014-05-06T14:17:48.621000-0400"
	                        },
	                        "State": "RUNNING",
	                        "StateChangeReason": {
	                            "Message": ""
	                        }
	                    },
	                    "Name": "Core instance group",
	                    "InstanceGroupType": "CORE",
	                    "InstanceType": "m1.small",
	                    "Id": "ig-DEF",
	                    "Market": "ON_DEMAND",
	                    "RunningInstanceCount": 2
	                }
	            ],
	            "Applications": [
	                {
	                    "Version": "1.0.3",
	                    "Name": "hadoop"
	                }
	            ],
	            "BootstrapActions": [],
	            "VisibleToAllUsers": false,
	            "RequestedAmiVersion": "2.4.2",
	            "LogUri": "s3://myLogUri/",
	            "AutoTerminate": false,
	            "Id": "j-XXXXXXXX"
	        }
	    }
