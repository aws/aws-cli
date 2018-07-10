Most of these examples assume that you specified your Amazon EMR service role and Amazon EC2 instance profile. If you have not done this, you must specify each required IAM role or use the ``--use-default-roles`` parameter when creating your cluster. For more information about specifying IAM roles, see the following topic in the Amazon EMR Management Guide:

http://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-iam-roles-launch-jobflow.html

**Quick start: create a cluster**

Command::

   aws emr create-cluster --release-label emr-5.14.0 --instance-type m4.large --instance-count 2

**Create an Amazon EMR cluster with default ServiceRole and InstanceProfile roles**

Create an Amazon EMR cluster that uses the ``--instance-groups`` configuration.

Command::

   aws emr create-cluster --release-label emr-5.14.0 --service-role EMR_DefaultRole --ec2-attributes InstanceProfile=EMR_EC2_DefaultRole --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large

Create an Amazon EMR cluster that uses the ``--instance-fleets`` configuration, specifying two instance types for each fleet and two EC2 Subnets.

Command::

   aws emr create-cluster --release-label emr-5.14.0 --service-role EMR_DefaultRole --ec2-attributes InstanceProfile=EMR_EC2_DefaultRole,SubnetIds=['subnet-ab12345c','subnet-de67890f'] --instance-fleets InstanceFleetType=MASTER,TargetOnDemandCapacity=1,InstanceTypeConfigs=['{InstanceType=m4.large}'] InstanceFleetType=CORE,TargetSpotCapacity=11,InstanceTypeConfigs=['{InstanceType=m4.large,BidPrice=0.5,WeightedCapacity=3}','{InstanceType=m4.2xlarge,BidPrice=0.9,WeightedCapacity=5}'],LaunchSpecifications={SpotSpecification='{TimeoutDurationMinutes=120,TimeoutAction=SWITCH_TO_ON_DEMAND}'}

**Create a cluster with default roles**

The following example uses the ``--use-default-roles`` parameter to specify the default service role and instance profile.

Command::

    aws emr create-cluster --release-label emr-5.9.0 --use-default-roles --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large --auto-terminate

**Create a cluster and specify the applications to install**

Use the ``--applications`` parameter to specify the applications that Amazon EMR installs. The following example installs Hadoop, Hive and Pig.

Command::

   aws emr create-cluster --applications Name=Hadoop Name=Hive Name=Pig --release-label emr-5.9.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large --auto-terminate

The following example installs Spark.

Command::

	 aws emr create-cluster --release-label emr-5.9.0 --applications Name=Spark --ec2-attributes KeyName=myKey --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large --auto-terminate

**Specify a custom AMI to use for cluster instances**

The following example creates a cluster instance based on the Amazon Linux AMI with ID ``ami-a518e6df``.

Command::

  aws emr create-cluster --name "Cluster with My Custom AMI" --custom-ami-id ami-a518e6df --ebs-root-volume-size 20 --release-label emr-5.9.0 --use-default-roles --instance-count 2 --instance-type m4.large

**Customize application configurations**

The following examples use the ``--configurations`` parameter to specify a JSON configuration file that contains application customizations for Hadoop. For more information, see http://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-configure-apps.html.

The following example specifies ``configurations.json`` as a local file.

Command::

    aws emr create-cluster --configurations file://configurations.json --release-label emr-5.9.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large --auto-terminate

The following example specifies ``configurations.json`` as a file in Amazon S3.

Command::

    aws emr create-cluster --configurations https://s3.amazonaws.com/myBucket/configurations.json --release-label emr-5.9.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large --auto-terminate

The following demonstrates example contents of ``configurations.json``.

::

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

**Create a cluster with master, core, and task instance groups**

The following example creates a cluster, using ``--instance-groups`` to specify the type and number of EC2 instances to use for master, core, and task instance groups

Command::

    aws emr create-cluster --release-label emr-5.9.0 --instance-groups Name=Master,InstanceGroupType=MASTER,InstanceType=m4.large,InstanceCount=1 Name=Core,InstanceGroupType=CORE,InstanceType=m4.large,InstanceCount=2 Name=Task,InstanceGroupType=TASK,InstanceType=m4.large,InstanceCount=2

**Specify that a cluster should terminate after completing all steps**

The following example uses ``--auto-terminate`` to specify that the cluster should shut down automatically after completing all steps.

Command::

    aws emr create-cluster --release-label emr-5.9.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large  InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large --auto-terminate

**Specify cluster configuration details such as the Amazon EC2 key pair, network configuration, and security groups**

The following example creates a cluster with the Amazon EC2 key pair named ``myKey`` and a customized instance profile named ``myProfile``. Key pairs are used to authorize SSH connections to cluster nodes, most often the master node. For more information, see http://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-access-ssh.html.

Command::

    aws emr create-cluster --ec2-attributes KeyName=myKey,InstanceProfile=myProfile --release-label emr-5.9.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large --auto-terminate

The following example creates a cluster in an Amazon VPC subnet.

Command::

    aws emr create-cluster --ec2-attributes SubnetId=subnet-xxxxx --release-label emr-5.9.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large --auto-terminate

The following example creates a cluster in the ``us-east-1b`` availability zone.

Command::

    aws emr create-cluster --ec2-attributes AvailabilityZone=us-east-1b --release-label emr-5.9.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large

The following example creates a cluster and specifies only the Amazon EMR-managed security groups.

Command::

    aws emr create-cluster --release-label emr-5.9.0 --service-role myServiceRole --ec2-attributes InstanceProfile=myRole,EmrManagedMasterSecurityGroup=sg-master1,EmrManagedSlaveSecurityGroup=sg-slave1 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large

The following example creates a cluster and specifies only additional Amazon EC2 security groups.

Command::

    aws emr create-cluster --release-label emr-5.9.0 --service-role myServiceRole --ec2-attributes InstanceProfile=myRole,AdditionalMasterSecurityGroups=[sg-addMaster1,sg-addMaster2,sg-addMaster3,sg-addMaster4],AdditionalSlaveSecurityGroups=[sg-addSlave1,sg-addSlave2,sg-addSlave3,sg-addSlave4] --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large

The following example creates a cluster and specifies the EMR-Managed security groups, as well as additional security groups.

Command::

	  aws emr create-cluster --release-label emr-5.9.0 --service-role myServiceRole --ec2-attributes InstanceProfile=myRole,EmrManagedMasterSecurityGroup=sg-master1,EmrManagedSlaveSecurityGroup=sg-slave1,AdditionalMasterSecurityGroups=[sg-addMaster1,sg-addMaster2,sg-addMaster3,sg-addMaster4],AdditionalSlaveSecurityGroups=[sg-addSlave1,sg-addSlave2,sg-addSlave3,sg-addSlave4] --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large

The following example creates a cluster in a VPC private subnet and use a specific Amazon EC2 security group to enable Amazon EMR service access, which is required for clusters in private subnets.

Command::

    aws  emr create-cluster --release-label emr-5.9.0 --service-role myServiceRole --ec2-attributes InstanceProfile=myRole,ServiceAccessSecurityGroup=sg-service-access,EmrManagedMasterSecurityGroup=sg-master,EmrManagedSlaveSecurityGroup=sg-slave --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large


The following example specifies security group configuration parameters within a JSON file, ``ec2_attributes.json``, that is stored locally.

Command::

    aws emr create-cluster --release-label emr-5.9.0 --service-role myServiceRole --ec2-attributes file://ec2_attributes.json  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large

The following example demonstrates the contents of ``ec2_attributes.json``.

::

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

**Enable debugging and specify a log URI**

The following example uses the ``--enable-debugging`` parameter, which allows you to view log files more easily using the debugging tool in the Amazon EMR console. The ``--log-uri`` parameter is required with ``--enable-debugging``.

Command::

    aws emr create-cluster --enable-debugging --log-uri s3://myBucket/myLog --release-label emr-5.9.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large --auto-terminate

**Add tags when creating a cluster**

Tags are key-value pairs that help you identify and manage clusters. The following example uses the ``--tags`` parameter to create two tags for a cluster, one with the key name ``name`` and the value ``Shirley Rodriguez`` and the other with the key name ``address`` and the value ``123 Maple Street, Anytown, USA``.

Command::

    aws emr create-cluster --tags name="Shirley Rodriguez" age=29 department="Analytics" --release-label emr-5.9.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large --auto-terminate

The following example lists the tags applied to a cluster.

Command::

    aws emr describe-cluster --cluster-id j-XXXXXXYY --query Cluster.Tags

**Use a security configuration to enable encryption and other security features**

The following example uses the ``--security-configuration`` parameter to specify a security configuration for an EMR cluster. You can use security configurations with Amazon EMR version 4.8.0 or later.

Command::

    aws emr create-cluster --instance-type m4.large --release-label emr-5.9.0 --security-configuration mySecurityConfiguration

**Create a cluster with additional EBS storage volumes configured for the instance groups**

Wnen specifying additional EBS volumes, the following arguments are required: ``VolumeType``, ``SizeInGB`` if ``EbsBlockDeviceConfigs`` is specified.

The following example creates a cluster with multiple EBS volumes attached to EC2 instances in the core instance group.

Command::

    aws emr create-cluster --release-label emr-5.9.0  --use-default-roles --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=d2.xlarge 'InstanceGroupType=CORE,InstanceCount=2,InstanceType=d2.xlarge,EbsConfiguration={EbsOptimized=true,EbsBlockDeviceConfigs=[{VolumeSpecification={VolumeType=gp2,SizeInGB=100}},{VolumeSpecification={VolumeType=io1,SizeInGB=100,Iops=100},VolumesPerInstance=4}]}' --auto-terminate

The following example creates a cluster with multiple EBS volumes attached to EC2 instances in the master instance group.

Command::

    aws emr create-cluster --release-label emr-5.9.0 --use-default-roles --instance-groups 'InstanceGroupType=MASTER, InstanceCount=1, InstanceType=d2.xlarge, EbsConfiguration={EbsOptimized=true, EbsBlockDeviceConfigs=[{VolumeSpecification={VolumeType=io1, SizeInGB=100, Iops=100}},{VolumeSpecification={VolumeType=standard,SizeInGB=50},VolumesPerInstance=3}]}' InstanceGroupType=CORE,InstanceCount=2,InstanceType=d2.xlarge --auto-terminate


**Create a cluster with an automatic scaling policy**

You can attach automatic scaling policies to core and task instance groups using Amazon EMR version 4.0 and later. The automatic scaling policy dynamically adds and removes EC2 instances in response to an Amazon CloudWatch metric. For more information, see http://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-automatic-scaling.html.

When attaching an automatic scaling policy, you must also specify the default role for automatic scaling using ``--auto-scaling-role EMR_AutoScaling_DefaultRole``.

The following example specifies the automatic scaling policy for the ``CORE`` instance group using the ``AutoScalingPolicy`` argument with an embedded JSON structure, which specifies the scaling policy configuration. Instance groups with an embedded JSON structure must have the entire collection of arguments enclosed in single quotes. Using single quotes is optional for instance groups without an embedded JSON structure.

Command::

    aws emr create-cluster --release-label emr-5.9.0 --use-default-roles --auto-scaling-role EMR_AutoScaling_DefaultRole --instance-groups InstanceGroupType=MASTER,InstanceType=d2.xlarge,InstanceCount=1 'InstanceGroupType=CORE,InstanceType=d2.xlarge,InstanceCount=2,AutoScalingPolicy={Constraints={MinCapacity=1,MaxCapacity=5},Rules=[{Name=TestRule,Description=TestDescription,Action={Market=ON_DEMAND,SimpleScalingPolicyConfiguration={AdjustmentType=EXACT_CAPACITY,ScalingAdjustment=2}},Trigger={CloudWatchAlarmDefinition={ComparisonOperator=GREATER_THAN,EvaluationPeriods=5,MetricName=TestMetric,Namespace=EMR,Period=3,Statistic=MAXIMUM,Threshold=4.5,Unit=NONE,Dimensions=[{Key=TestKey,Value=TestValue}]}}}]}'

The following example uses a JSON file, ``instancegroupconfig.json``, to specify the configuration of all instance groups in a cluster. The JSON file specifies the automatic scaling policy configuration for the core instance group.

Command::

   aws emr create-cluster --release-label emr-5.9.0 --service-role EMR_DefaultRole --ec2-attributes InstanceProfile=EMR_EC2_DefaultRole --instance-groups s3://mybucket/instancegroupconfig.json --auto-scaling-role EMR_AutoScaling_DefaultRole

The following example shows the contents of ``instancegroupconfig.json``.

::

  [
    {
        "InstanceCount": 1,
        "Name": "MyMasterIG",
        "InstanceGroupType": "MASTER",
        "InstanceType": "m4.large"
    },
    {
        "InstanceCount": 2,
        "Name": "MyCoreIG",
        "InstanceGroupType": "CORE",
        "InstanceType": "m4.large",
        "AutoScalingPolicy": {
            "Constraints": {
                "MinCapacity": 2,
                "MaxCapacity": 10
            },
            "Rules": [
                {
                    "Name": "Default-scale-out",
                    "Description": "Replicates the default scale-out rule in the console for YARN memory.",
                    "Action": {
                        "SimpleScalingPolicyConfiguration": {
                            "AdjustmentType": "CHANGE_IN_CAPACITY",
                            "ScalingAdjustment": 1,
                            "CoolDown": 300
                        }
                    },
                    "Trigger": {
                        "CloudWatchAlarmDefinition": {
                            "ComparisonOperator": "LESS_THAN",
                            "EvaluationPeriods": 1,
                            "MetricName": "YARNMemoryAvailablePercentage",
                            "Namespace": "AWS/ElasticMapReduce",
                            "Period": 300,
                            "Threshold": 15,
                            "Statistic": "AVERAGE",
                            "Unit": "PERCENT",
                            "Dimensions": [
                                {
                                    "Key": "JobFlowId",
                                    "Value": "${emr.clusterId}"
                                }
                            ]
                        }
                    }
                }
            ]
        }
    }
   ]

**Add custom JAR steps when creating a cluster**

The following example adds steps by specifying a JAR file stored in Amazon S3. Steps submit work to a cluster. The main function defined in the JAR file executes after EC2 instances are provisioned, any bootstrap actions have executed, and applications are installed. The steps are specified using ``Type=CUSTOM_JAR``.

Custom JAR steps required the ``Jar=`` parameter, which specifies the path and file name of the JAR. Optional parameters are the following.

::

    Type, Name, ActionOnFailure, Args, MainClass

If main class is not specified, the JAR file should specify Main-Class in its manifest file.

Command::

    aws emr create-cluster --steps Type=CUSTOM_JAR,Name=CustomJAR,ActionOnFailure=CONTINUE,Jar=s3://myBucket/mytest.jar,Args=arg1,arg2,arg3 Type=CUSTOM_JAR,Name=CustomJAR,ActionOnFailure=CONTINUE,Jar=s3://myBucket/mytest.jar,MainClass=mymainclass,Args=arg1,arg2,arg3  --release-label emr-5.3.1  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large --auto-terminate


**Add streaming steps when creating a cluster**

The following examples add a streaming step to a cluster that terminates after all steps run.

Streaming steps required parameters.

::

    Type, Args

Streaming steps optional parameters.

::

    Name, ActionOnFailure

The following example adds specifies the step inline.

Command::

    aws emr create-cluster --steps Type=STREAMING,Name='Streaming Program',ActionOnFailure=CONTINUE,Args=[-files,s3://elasticmapreduce/samples/wordcount/wordSplitter.py,-mapper,wordSplitter.py,-reducer,aggregate,-input,s3://elasticmapreduce/samples/wordcount/input,-output,s3://mybucket/wordcount/output] --release-label emr-5.3.1  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large --auto-terminate

The following example uses a JSON configuration file, ``multiplefiles.json``, which is stored locally. The JSON configuration specifies multiple files. To specify multiple files within a step, you must use a JSON configuration file to specify the step.

Command::

   aws emr create-cluster --steps file://./multiplefiles.json --release-label emr-5.9.0  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large --auto-terminate

The following example demonstrates the contents of ``multiplefiles.json``.

::

  [
    {
        "Name": "JSON Streaming Step",
        "Args": [
            "-files",
            "s3://elasticmapreduce/samples/wordcount/wordSplitter.py",
            "-mapper",
            "wordSplitter.py",
            "-reducer",
            "aggregate",
            "-input",
            "s3://elasticmapreduce/samples/wordcount/input",
            "-output",
            "s3://mybucket/wordcount/output"
        ],
        "ActionOnFailure": "CONTINUE",
        "Type": "STREAMING"
    }
  ]

NOTE: JSON arguments must include options and values as their own items in the list.

**Add Hive steps when creating a cluster**

Command::

    aws emr create-cluster --steps Type=HIVE,Name='Hive program',ActionOnFailure=CONTINUE,ActionOnFailure=TERMINATE_CLUSTER,Args=[-f,s3://elasticmapreduce/samples/hive-ads/libs/model-build.q,-d,INPUT=s3://elasticmapreduce/samples/hive-ads/tables,-d,OUTPUT=s3://mybucket/hive-ads/output/2014-04-18/11-07-32,-d,LIBS=s3://elasticmapreduce/samples/hive-ads/libs] --applications Name=Hive --release-label emr-5.3.1  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large

Hive steps required parameters.

::

    Type, Args

Hive steps optional parameters.

::

    Name, ActionOnFailure

**Add Pig steps when creating a cluster**

Command::

    aws emr create-cluster --steps Type=PIG,Name='Pig program',ActionOnFailure=CONTINUE,Args=[-f,s3://elasticmapreduce/samples/pig-apache/do-reports2.pig,-p,INPUT=s3://elasticmapreduce/samples/pig-apache/input,-p,OUTPUT=s3://mybucket/pig-apache/output] --applications Name=Pig --release-label emr-5.3.1  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large

Pig steps required parameters.

::

    Type, Args

Pig steps optional parameters.

::

    Name, ActionOnFailure

**Add bootstrap actions**

The following example runs two bootstrap actions defined as scripts that are stored in Amazon S3.

Command::

    aws emr create-cluster --bootstrap-actions Path=s3://mybucket/myscript1,Name=BootstrapAction1,Args=[arg1,arg2] Path=s3://mybucket/myscript2,Name=BootstrapAction2,Args=[arg1,arg2] --release-label emr-5.3.1  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m4.large InstanceGroupType=CORE,InstanceCount=2,InstanceType=m4.large --auto-terminate

**Enable EMRFS consistent view and customize the RetryCount and RetryPeriod settings**

The following example specifies the retry count and retry period for EMRFS consistent view. The ``Consistent=true`` argument is required.

Command::

    aws emr create-cluster --instance-type m4.large --release-label emr-5.9.0 --emrfs Consistent=true,RetryCount=6,RetryPeriod=30

The following example specifies the same EMRFS configuration as the previous example, using a JSON configuration file, ``emrfsconfig.json``, stored locally.

Command::

   aws emr create-cluster --instance-type m4.large --release-label emr-5.9.0 --emrfs file://emrfsconfig.json


The following example demonstrates the contents of ``emrfsconfig.json``.

::

    {
      "Consistent": true,
      "RetryCount": 6,
      "RetryPeriod": 30
    }

**Create a cluster with Kerberos configured**

The following examples create a cluster using a security configuration with Kerberos enabled, and establishes Kerberos parameters for the cluster using ``--kerberos-attributes``.

The following command specifies Kerberos attributes for the cluster inline.

Command::

    aws emr create-cluster --instance-type m3.xlarge --release-label emr-5.10.0 --service-role EMR_DefaultRole --ec2-attributes InstanceProfile=EMR_EC2_DefaultRole --security-configuration mySecurityConfiguration --kerberos-attributes Realm=EC2.INTERNAL,KdcAdminPassword=123,CrossRealmTrustPrincipalPassword=123

The following command specifies the same attributes, but references a JSON file, ``kerberos_attributes.json``, for the properties and values. In this example, the file is saved in the same directory where you run the command. You can also reference a configuration file saved in Amazon S3.

Command::

    aws emr create-cluster --instance-type m3.xlarge --release-label emr-5.10.0 --service-role EMR_DefaultRole --ec2-attributes InstanceProfile=EMR_EC2_DefaultRole --security-configuration mySecurityConfiguration --kerberos-attributes file://kerberos_attributes.json

The contents of ``kerberos_attributes.json`` are shown below:

::

    {
      "Realm": "EC2.INTERNAL",
      "KdcAdminPassword": "123",
      "CrossRealmTrustPrincipalPassword": "123",
    }
