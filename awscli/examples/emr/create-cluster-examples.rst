Note: some of these examples assume that you have specified your Amazon EMR service role and Amazon EC2 instance profile in the AWS CLI configuration file. If you have not done this, you must specify each required IAM role or use the --use-default-roles parameter when creating your cluster. You can learn more about specifying parameter values for Amazon EMR commands here:
http://docs.aws.amazon.com/ElasticMapReduce/latest/DeveloperGuide/emr-aws-cli-config.html

**1. Quick start: to create an Amazon EMR cluster**

- Command::

    aws emr create-cluster --release-label emr-5.3.1  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**2. Create an Amazon EMR cluster with default ServiceRole and InstanceProfile roles**

- Create an Amazon EMR cluster that uses the --instance-groups configuration::

  aws emr create-cluster --release-label emr-5.3.1  --service-role EMR_DefaultRole --ec2-attributes InstanceProfile=EMR_EC2_DefaultRole --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge

- Create an Amazon EMR cluster that uses the --instance-fleets configuration, specifying two instance types for each fleet and two EC2 Subnets::

  aws emr create-cluster --release-label emr-5.3.1 --service-role EMR_DefaultRole --ec2-attributes InstanceProfile=EMR_EC2_DefaultRole,SubnetIds=['subnet-ab12345c','subnet-de67890f'] --instance-fleets InstanceFleetType=MASTER,TargetOnDemandCapacity=1,InstanceTypeConfigs=['{InstanceType=m3.xlarge}'] InstanceFleetType=CORE,TargetSpotCapacity=11,InstanceTypeConfigs=['{InstanceType=m3.xlarge,BidPrice=0.5,WeightedCapacity=3}','{InstanceType=m4.2xlarge,BidPrice=0.9,WeightedCapacity=5}'],LaunchSpecifications={SpotSpecification='{TimeoutDurationMinutes=120,TimeoutAction=SWITCH_TO_ON_DEMAND}'}

**3. Create an Amazon EMR cluster with default roles**

- Command::

    aws emr create-cluster --release-label emr-5.3.1  --use-default-roles --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**4. Create an Amazon EMR cluster with applications**

- Create an Amazon EMR cluster with Hadoop, Hive and Pig installed::

  aws emr create-cluster --applications Name=Hadoop Name=Hive Name=Pig --release-label emr-5.3.1  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Create an Amazon EMR cluster with Spark installed:

	 aws emr create-cluster --release-label emr-5.3.1 --applications Name=Spark --ec2-attributes KeyName=myKey --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**5. Change configuration for Hadoop MapReduce**

The following example changes the maximum number of map tasks and sets the NameNode heap size:

- Specifying configurations from a local file::

    aws emr create-cluster --configurations file://configurations.json --release-label emr-5.3.1 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Specifying configurations from a file in Amazon S3::

    aws emr create-cluster --configurations https://s3.amazonaws.com/myBucket/configurations.json --release-label emr-5.3.1 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Contents of configurations.json::

    [
     {
       "Classification": "mapred-site",
       "Properties": {
           "mapred.tasktracker.map.tasks.maximum": 2
       }
     },
     {
       "Classification": "hadoop-env",
       "Properties": {},
       "Configurations": [
           {
             "Classification": "export",
             "Properties": {
                 "HADOOP_DATANODE_HEAPSIZE": 2048,
                 "HADOOP_NAMENODE_OPTS": "-XX:GCTimeRatio=19"
             }
           }
       ]
     }
    ]

**6. Create an Amazon EMR cluster with MASTER, CORE, and TASK instance groups**

- Command::

    aws emr create-cluster --release-label emr-5.3.1  --auto-terminate --instance-groups Name=Master,InstanceGroupType=MASTER,InstanceType=m3.xlarge,InstanceCount=1 Name=Core,InstanceGroupType=CORE,InstanceType=m3.xlarge,InstanceCount=2 Name=Task,InstanceGroupType=TASK,InstanceType=m3.xlarge,InstanceCount=2

**7. Specify whether the cluster should terminate after completing all the steps**

- Create an Amazon EMR cluster that terminates after completing all the steps::

    aws emr create-cluster --release-label emr-5.3.1   --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge  InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**8. Specify EC2 Attributes**

- Create an Amazon EMR cluster with the Amazon EC2 key pair "myKey" and instance profile "myProfile"::

    aws emr create-cluster --ec2-attributes KeyName=myKey,InstanceProfile=myProfile --release-label emr-5.3.1   --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Create an Amazon EMR cluster in an Amazon VPC subnet::

    aws emr create-cluster --ec2-attributes SubnetId=subnet-xxxxx --release-label emr-5.3.1   --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Create an Amazon EMR cluster in an Availability Zone. For example, us-east-1b::

    aws emr create-cluster --ec2-attributes AvailabilityZone=us-east-1b --release-label emr-5.3.1  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge

- Create an Amazon EMR cluster specifying the Amazon EC2 security groups::

	aws emr create-cluster --release-label emr-5.3.1 --service-role myServiceRole --ec2-attributes InstanceProfile=myRole,EmrManagedMasterSecurityGroup=sg-master1,EmrManagedSlaveSecurityGroup=sg-slave1,AdditionalMasterSecurityGroups=[sg-addMaster1,sg-addMaster2,sg-addMaster3,sg-addMaster4],AdditionalSlaveSecurityGroups=[sg-addSlave1,sg-addSlave2,sg-addSlave3,sg-addSlave4] --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge

- Create an Amazon EMR cluster specifying only the Amazon EMR-managed Amazon EC2 security groups::

	aws emr create-cluster --release-label emr-5.3.1 --service-role myServiceRole --ec2-attributes InstanceProfile=myRole,EmrManagedMasterSecurityGroup=sg-master1,EmrManagedSlaveSecurityGroup=sg-slave1 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge

- Create an Amazon EMR cluster specifying only the additional Amazon EC2 security groups::

    aws emr create-cluster --release-label emr-5.3.1 --service-role myServiceRole --ec2-attributes InstanceProfile=myRole,AdditionalMasterSecurityGroups=[sg-addMaster1,sg-addMaster2,sg-addMaster3,sg-addMaster4],AdditionalSlaveSecurityGroups=[sg-addSlave1,sg-addSlave2,sg-addSlave3,sg-addSlave4] --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge

- Create an Amazon EMR cluster in a VPC private subnet and use a specific Amazon EC2 security group to enable the Amazon EMR service access (required for clusters in private subnets)::

    aws  emr create-cluster --release-label emr-5.3.1 --service-role myServiceRole --ec2-attributes InstanceProfile=myRole,ServiceAccessSecurityGroup=sg-service-access,EmrManagedMasterSecurityGroup=sg-master,EmrManagedSlaveSecurityGroup=sg-slave --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge


- JSON equivalent (contents of ec2_attributes.json)::

    [
     {
       "SubnetId": "subnet-xxxxx",
       "KeyName": "myKey",
       "InstanceProfile":"myRole",
       "EmrManagedMasterSecurityGroup": "sg-master1",
       "EmrManagedSlaveSecurityGroup": "sg-slave1",
       "ServiceAccessSecurityGroup": "sg-service-access"
       "AdditionalMasterSecurityGroups": ["sg-addMaster1","sg-addMaster2","sg-addMaster3","sg-addMaster4"],
       "AdditionalSlaveSecurityGroups": ["sg-addSlave1","sg-addSlave2","sg-addSlave3","sg-addSlave4"]
     }
   ]

NOTE: JSON arguments must include options and values as their own items in the list.

- Command (using ec2_attributes.json)::

	aws emr create-cluster --release-label emr-5.3.1 --service-role myServiceRole --ec2-attributes file://./ec2_attributes.json  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge

**9. Enable debugging and specify a Log URI**

- Command::

    aws emr create-cluster --enable-debugging --log-uri s3://myBucket/myLog  --release-label emr-5.3.1  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**10. Add tags when creating an Amazon EMR cluster**

- Add a list of tags::

    aws emr create-cluster --tags name="John Doe" age=29 address="123 East NW Seattle" --release-label emr-5.3.1  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- List tags of an Amazon EMR cluster::

    aws emr describe-cluster --cluster-id j-XXXXXXYY --query Cluster.Tags

**11. Use a security configuration to enable encryption**

- Command::

    aws emr create-cluster --instance-type m3.xlarge --release-label emr-5.3.1 --security-configuration mySecurityConfiguration

**12. To create an Amazon EMR cluster with EBS volumes configured to the instance groups**

- Create a cluster with multiple EBS volumes attached to the CORE instance group. EBS volumes can be attached to MASTER, CORE, and TASK instance groups. For instance groups with EBS configurations, which have an embedded JSON structure, you should enclose the entire instance group argument with single quotes. For instance groups with no EBS configuration, using single quotes is optional.

- Command::

    aws emr create-cluster --release-label emr-5.3.1  --use-default-roles --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=d2.xlarge 'InstanceGroupType=CORE,InstanceCount=2,InstanceType=d2.xlarge,EbsConfiguration={EbsOptimized=true,EbsBlockDeviceConfigs=[{VolumeSpecification={VolumeType=gp2,SizeInGB=100}},{VolumeSpecification={VolumeType=io1,SizeInGB=100,Iops=100},VolumesPerInstance=4}]}' --auto-terminate

- Create a cluster with multiple EBS volumes attached to the MASTER instance group.

- Command::

    aws emr create-cluster --release-label emr-5.3.1 --use-default-roles --instance-groups 'InstanceGroupType=MASTER, InstanceCount=1, InstanceType=d2.xlarge, EbsConfiguration={EbsOptimized=true, EbsBlockDeviceConfigs=[{VolumeSpecification={VolumeType=io1, SizeInGB=100, Iops=100}},{VolumeSpecification={VolumeType=standard,SizeInGB=50},VolumesPerInstance=3}]}' InstanceGroupType=CORE,InstanceCount=2,InstanceType=d2.xlarge --auto-terminate

- Required parameters::

    VolumeType, SizeInGB if EbsBlockDeviceConfigs specified

- Create a cluster with an Auto Scaling policy attached to the CORE instance group. The Auto Scaling policy can be attached to CORE and TASK instance groups. For instance groups with an Auto Scaling policy attached, you should enclose the entire instance group argument with single quotes. For instance groups with no Auto Scaling policy, using single quotes is optional.

- Command::

    aws emr create-cluster --release-label emr-5.3.1 --use-default-roles --auto-scaling-role EMR_AutoScaling_DefaultRole --instance-groups InstanceGroupType=MASTER,InstanceType=d2.xlarge,InstanceCount=1 'InstanceGroupType=CORE,InstanceType=d2.xlarge,InstanceCount=2,AutoScalingPolicy={Constraints={MinCapacity=1,MaxCapacity=5},Rules=[{Name=TestRule,Description=TestDescription,Action={Market=ON_DEMAND,SimpleScalingPolicyConfiguration={AdjustmentType=EXACT_CAPACITY,ScalingAdjustment=2}},Trigger={CloudWatchAlarmDefinition={ComparisonOperator=GREATER_THAN,EvaluationPeriods=5,MetricName=TestMetric,Namespace=EMR,Period=3,Statistic=MAXIMUM,Threshold=4.5,Unit=NONE,Dimensions=[{Key=TestKey,Value=TestValue}]}}}]}'

**13. To add custom JAR steps to a cluster when creating an Amazon EMR cluster**

- Command::

    aws emr create-cluster --steps Type=CUSTOM_JAR,Name=CustomJAR,ActionOnFailure=CONTINUE,Jar=s3://myBucket/mytest.jar,Args=arg1,arg2,arg3 Type=CUSTOM_JAR,Name=CustomJAR,ActionOnFailure=CONTINUE,Jar=s3://myBucket/mytest.jar,MainClass=mymainclass,Args=arg1,arg2,arg3  --release-label emr-5.3.1  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Custom JAR steps required parameters::

    Jar

- Custom JAR steps optional parameters::

    Type, Name, ActionOnFailure, Args

**14. To add streaming steps when creating an Amazon EMR cluster**

- Command::

    aws emr create-cluster --steps Type=STREAMING,Name='Streaming Program',ActionOnFailure=CONTINUE,Args=[-files,s3://elasticmapreduce/samples/wordcount/wordSplitter.py,-mapper,wordSplitter.py,-reducer,aggregate,-input,s3://elasticmapreduce/samples/wordcount/input,-output,s3://mybucket/wordcount/output] --release-label emr-5.3.1  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Streaming steps required parameters::

    Type, Args

- Streaming steps optional parameters::

    Name, ActionOnFailure

- JSON equivalent (contents of step.json)::

    [
     {
       "Name": "JSON Streaming Step",
       "Args": ["-files","s3://elasticmapreduce/samples/wordcount/wordSplitter.py","-mapper","wordSplitter.py","-reducer","aggregate","-input","s3://elasticmapreduce/samples/wordcount/input","-output","s3://mybucket/wordcount/output"],
       "ActionOnFailure": "CONTINUE",
       "Type": "STREAMING"
     }
   ]

NOTE: JSON arguments must include options and values as their own items in the list.

- Command (using step.json)::

    aws emr create-cluster --steps file://./step.json --release-label emr-4.0.0  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**15. To use multiple files in a streaming step (JSON only)**

- JSON (multiplefiles.json)::

   [
     {
        "Name": "JSON Streaming Step",
        "Type": "STREAMING",
        "ActionOnFailure": "CONTINUE",
        "Args": [
            "-files",
            "s3://mybucket/mapper.py,s3://mybucket/reducer.py",
            "-mapper",
            "mapper.py",
            "-reducer",
            "reducer.py",
            "-input",
            "s3://mybucket/input",
            "-output",
            "s3://mybucket/output"]
     }
   ]

- Command::

    aws emr create-cluster --steps file://./multiplefiles.json --release-label emr-5.3.1 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**16. To add Hive steps when creating an Amazon EMR cluster**

- Command::

    aws emr create-cluster --steps Type=HIVE,Name='Hive program',ActionOnFailure=CONTINUE,ActionOnFailure=TERMINATE_CLUSTER,Args=[-f,s3://elasticmapreduce/samples/hive-ads/libs/model-build.q,-d,INPUT=s3://elasticmapreduce/samples/hive-ads/tables,-d,OUTPUT=s3://mybucket/hive-ads/output/2014-04-18/11-07-32,-d,LIBS=s3://elasticmapreduce/samples/hive-ads/libs] --applications Name=Hive --release-label emr-5.3.1  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge

- Hive steps required parameters::

    Type, Args

- Hive steps optional parameters::

    Name, ActionOnFailure

**17. To add Pig steps when creating an Amazon EMR cluster**

- Command::

    aws emr create-cluster --steps Type=PIG,Name='Pig program',ActionOnFailure=CONTINUE,Args=[-f,s3://elasticmapreduce/samples/pig-apache/do-reports2.pig,-p,INPUT=s3://elasticmapreduce/samples/pig-apache/input,-p,OUTPUT=s3://mybucket/pig-apache/output] --applications Name=Pig --release-label emr-5.3.1  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge

- Pig steps required parameters::

    Type, Args

- Pig steps optional parameters::

    Name, ActionOnFailure

**18. Add a list of bootstrap actions when creating an Amazon EMR Cluster**

- Command::

    aws emr create-cluster --bootstrap-actions Path=s3://mybucket/myscript1,Name=BootstrapAction1,Args=[arg1,arg2] Path=s3://mybucket/myscript2,Name=BootstrapAction2,Args=[arg1,arg2] --release-label emr-5.3.1  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**19. To enable consistent view in EMRFS and change the RetryCount and Retry Period settings when creating an Amazon EMR cluster**

- Command::

    aws emr create-cluster --instance-type m3.xlarge --release-label emr-5.3.1 --emrfs Consistent=true,RetryCount=5,RetryPeriod=30

- Required parameters::

    Consistent=true

- JSON equivalent (contents of emrfs.json)::

    {
      "Consistent": true,
      "RetryCount": 5,
      "RetryPeriod": 30
    }

- Command (Using emrfs.json)::

    aws emr create-cluster --instance-type m3.xlarge --release-label emr-5.3.1 --emrfs file://emrfs.json


**20. To enable consistent view with arguments e.g. change the DynamoDB read and write capacity when creating an Amazon EMR cluster**

- Command::

    aws emr create-cluster --instance-type m3.xlarge --release-label emr-5.3.1 --emrfs Consistent=true,RetryCount=5,RetryPeriod=30,Args=[fs.s3.consistent.metadata.read.capacity=600,fs.s3.consistent.metadata.write.capacity=300]

- Required parameters::

    Consistent=true

- JSON equivalent (contents of emrfs.json)::

    {
      "Consistent": true,
      "RetryCount": 5,
      "RetryPeriod": 30,
      "Args":["fs.s3.consistent.metadata.read.capacity=600", "fs.s3.consistent.metadata.write.capacity=300"]
    }

- Command (Using emrfs.json)::

    aws emr create-cluster --instance-type m3.xlarge --release-label emr-5.3.1 --emrfs file://emrfs.json

- Command (Using custom ami id)::

    aws emr create-cluster --instance-type m3.xlarge --release-label emr-5.3.1 --custom-ami-id ami-9be6f38c

- Command (Using custom EBS root volume)::

    aws emr create-cluster --instance-type m3.xlarge --release-label emr-5.3.1 --ebs-root-volume-size 20

- Command (Repo upgrade option on instance boot. This can be used only with custom AMIs)::

    aws emr create-cluster --instance-type m3.xlarge --release-label emr-5.3.1 --repo-upgrade-on-boot ${RepoUpgrade}

    RepoUpgrade {
       SECURITY,
       NONE
    }


**21. To create an Amazon EMR cluster with Kerberos configured**

- Command::

    aws emr create-cluster --instance-type m3.xlarge --release-label emr-5.10.0 --service-role EMR_DefaultRole --ec2-attributes InstanceProfile=EMR_EC2_DefaultRole --security-configuration mySecurityConfiguration --kerberos-attributes Realm=EC2.INTERNAL,KdcAdminPassword=123,CrossRealmTrustPrincipalPassword=123

- JSON equivalent (contents of kerberos_attributes.json)::

    {
      "Realm": "EC2.INTERNAL",
      "KdcAdminPassword": "123",
      "CrossRealmTrustPrincipalPassword": "123",
    }

- Command (Using kerberos_attributes.json)::

    aws emr create-cluster --instance-type m3.xlarge --release-label emr-5.10.0 --service-role EMR_DefaultRole --ec2-attributes InstanceProfile=EMR_EC2_DefaultRole --security-configuration mySecurityConfiguration --kerberos-attributes file://kerberos_attributes.json
