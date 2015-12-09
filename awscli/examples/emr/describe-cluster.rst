- Command::

    aws emr describe-cluster --cluster-id j-XXXXXXXX

- Output::

	For release-label based cluster:
	
		{
		    "Cluster": {
		        "Status": {
		            "Timeline": {
		                "ReadyDateTime": 1436475075.199, 
		                "CreationDateTime": 1436474656.563, 
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
		        "ReleaseLabel": "emr-4.0.0", 
		        "NormalizedInstanceHours": 96, 
		        "InstanceGroups": [
		            {
		                "RequestedInstanceCount": 2, 
		                "Status": {
		                    "Timeline": {
		                        "ReadyDateTime": 1436475074.245, 
		                        "CreationDateTime": 1436474656.564, 
		                        "EndDateTime": 1436638158.387
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
		                        "ReadyDateTime": 1436475074.245, 
		                        "CreationDateTime": 1436474656.564, 
		                        "EndDateTime": 1436638158.387
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


	For ami based cluster:
	
	    {
	        "Cluster": {
	            "Status": {
	                "Timeline": {
	                    "ReadyDateTime": 1399400564.432,
	                    "CreationDateTime": 1399400268.62
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
	            "RunningAmiVersion": "2.5.4",
	            "InstanceGroups": [
	                {
	                    "RequestedInstanceCount": 1,
	                    "Status": {
	                        "Timeline": {
	                            "ReadyDateTime": 1399400558.848,
	                            "CreationDateTime": 1399400268.621
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
	                            "ReadyDateTime": 1399400564.439,
	                            "CreationDateTime": 1399400268.621
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
