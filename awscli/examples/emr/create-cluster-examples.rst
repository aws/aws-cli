**1. Quick start: to create an Amazon EMR cluster**

- Command::

    aws emr create-cluster --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**2. Create an Amazon EMR cluster with MASTER, CORE, and TASK instance groups**

- Command::

	aws emr create-cluster --ami-version 3.1.0 --auto-terminate --instance-groups Name=Master,InstanceGroupType=MASTER,InstanceType=m3.xlarge,InstanceCount=1 Name=Core,InstanceGroupType=CORE,InstanceType=m3.xlarge,InstanceCount=2 Name=Task,InstanceGroupType=TASK,InstanceType=m3.xlarge,InstanceCount=2

**3. Specify whether the cluster should terminate after completing all the steps**

- Create an Amazon EMR cluster that will terminate after completing all the steps::

	aws emr create-cluster --ami-version 3.1.0  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge  InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Create an Amazon EMR cluster that will NOT terminate after completing all the steps::

	aws emr create-cluster --ami-version 3.1.0  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge  InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --no-auto-terminate

**4. Specify EC2 Attributes**

- Create an Amazon EMR cluster with Amazon EC2 Key Pair "myKey" and instance profile "myProfile"::

	aws emr create-cluster --ec2-attributes KeyName=myKey,InstanceProfile=myRole --ami-version 3.1.0  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Create an Amazon EMR cluster in an Amazon VPC subnet::

	aws emr create-cluster --ec2-attributes SubnetId=subnet-xxxxx --ami-version 3.1.0  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Create an Amazon EMR cluster in an AvailabilityZone. For example, us-west-1b::

	aws emr create-cluster --ec2-attributes AvailabilityZone=us-west-1b --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**5. Enable debugging and specify a Log URI**

- Command::

    aws emr create-cluster --enable-debugging --log-uri s3://myBucket/myLog  --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**6. Add tags when creating an Amazon EMR cluster**

- Add a list of tags::

	aws emr create-cluster --tags name="John Doe" age=29 address="123 East NW Seattle" --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- List tags of an Amazon EMR cluster::

    aws emr describe-cluster --cluster-id j-XXXXXXYY --query Cluster.Tags

**7. Add a list of bootstrap actions when creating an Amazon EMR Cluster**

- Command::

	aws emr create-cluster --bootstrap-actions Path=s3://mybucket/myscript1,Name=BootstrapAction1,Args=[arg1,arg2] Path=s3://mybucket/myscript2,Name=BootstrapAction2,Args=[arg1,arg2] --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- The following example changes the maximum number of map tasks and sets the NameNode heap size::

    aws emr create-cluster --bootstrap-actions Path=s3://elasticmapreduce/bootstrap-actions/configure-hadoop,Name="Change the maximum number of map tasks",Args=[-M,s3://myawsbucket/config.xml,-m,mapred.tasktracker.map.tasks.maximum=2] Path=s3://elasticmapreduce/bootstrap-actions/configure-daemons,Name="Set the NameNode heap size",Args=[--namenode-heap-size=2048,--namenode-opts=-XX:GCTimeRatio=19] --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**8. Create an Amazon EMR cluster with applications**

- Create an Amazon EMR cluster with Hive, Pig, HBase, Ganglia, and Impala installed::

	aws emr create-cluster --applications Name=Hive Name=Pig Name=HBase Name=Ganglia Name=Impala,Args=[IMPALA_BACKEND_PORT=22001,IMPALA_MEM_LIMIT=70%] --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Create an Amazon EMR cluster with Hive and Pig installed::

    aws emr create-cluster --applications Name=Hive,Version=0.11.0.1 Name=Pig,Version=0.11.1.1 --ami-version 2.4.2 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Create an Amazon EMR cluster with MapR M7 edition::

    aws emr create-cluster --applications Name=MapR,Args=--edition,m7,--version,3.0.2 --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**9. Restore HBase data from backup when creating an Amazon EMR cluster**

-Command::

    aws emr create-cluster --applications Name=HBase --restore-from-hbase-backup Dir=s3://myBucket/myBackup,BackupVersion=myBackupVersion --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**10. To add Custom JAR steps to a cluster when creating an Amazon EMR cluster**

- Command::

    aws emr create-cluster --steps Type=CUSTOM_JAR,Name=CustomJAR,ActionOnFailure=CONTINUE,Jar=s3://myBucket/mytest.jar,Args=arg1,arg2,arg3 Type=CUSTOM_JAR,Name=CustomJAR,ActionOnFailure=CONTINUE,Jar=s3://myBucket/mytest.jar,MainClass=mymainclass,Args=arg1,arg2,arg3  --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Custom JAR steps required parameters::

    Jar

- Custom JAR steps optional parameters::

    Type, Name, ActionOnFailure, Args

**11. To add Streaming steps when creating an Amazon EMR cluster**

- Command::
 
    aws emr create-cluster --steps Type=STREAMING,Name='Streaming Program',ActionOnFailure=CONTINUE,Args=-mapper,mymapper,-reducer,myreducer,-input,myinput,-output,myoutput Type=STREAMING,Name='Streaming Program',ActionOnFailure=CONTINUE,Args=--files,s3://elasticmapreduce/samples/wordcount/wordSplitter.py,-mapper,wordSplitter.py,-reducer,aggregate,-input,s3://elasticmapreduce/samples/wordcount/input,-output,s3://mybucket/wordcount/output --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Streaming steps required parameters::

    Type, Args

- Streaming steps optional parameters::

    Name, ActionOnFailure

**12. To add Hive steps when creating an Amazon EMR cluster**

- Command::

    aws emr create-cluster --steps Type=HIVE,Name='Hive program',ActionOnFailure=CONTINUE,Args=[-f,s3://mybuckey/myhivescript.q,-d,INPUT=s3://mybucket/myhiveinput,-d,OUTPUT=s3://mybucket/myhiveoutput,arg1,arg2] Type=HIVE,Name='Hive steps',ActionOnFailure=TERMINATE_CLUSTER,Args=[-f,s3://elasticmapreduce/samples/hive-ads/libs/model-build.q,-d,INPUT=s3://elasticmapreduce/samples/hive-ads/tables,-d,OUTPUT=s3://mybucket/hive-ads/output/2014-04-18/11-07-32,-d,LIBS=s3://elasticmapreduce/samples/hive-ads/libs] --applications Name=Hive --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Hive steps required parameters::

    Type, Args

- Hive steps optional parameters::

    Name, ActionOnFailure, Version

**13. To add Pig steps when creating an Amazon EMR cluster**

- Command::

    aws emr create-cluster --steps Type=PIG,Name='Pig program',ActionOnFailure=CONTINUE,Args=[-f,s3://mybuckey/mypigscript.pig,-p,INPUT=s3://mybucket/mypiginput,-p,OUTPUT=s3://mybucket/mypigoutput,arg1,arg2] Type=PIG,Name='Pig program',Args=[-f,s3://elasticmapreduce/samples/pig-apache/do-reports2.pig,-p,INPUT=s3://elasticmapreduce/samples/pig-apache/input,-p,OUTPUT=s3://mybucket/pig-apache/output,arg1,arg2] --applications Name=Pig --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Pig steps required parameters::

    Type, Args

- Pig steps optional parameters::

    Name, ActionOnFailure, Version

**14. To add Impala steps when creating an Amazon EMR cluster**

- Command::

    aws emr create-cluster --steps Type=IMPALA,Name='Impala program',ActionOnFailure=CONTINUE,Args=-f,--impala-script,s3://myimpala/input,--console-output-path,s3://myimpala/output Type=IMPALA,Name='Impala program',ActionOnFailure=CONTINUE,Args=-f,--impala-script,s3://myimpala/input,--console-output-path,s3://myimpala/output --applications Name=Impala --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Impala steps required parameters::

    Type, Args

- Impala steps optional parameters::

    Name, ActionOnFailure
