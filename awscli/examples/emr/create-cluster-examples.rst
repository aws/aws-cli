**1. Quick start: to create an Amazon EMR cluster**

- Command::

    aws emr create-cluster --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**2. Create an Amazon EMR cluster with ServiceRole and InstanceProfile**

- Command::

    aws emr create-cluster --ami-version 3.1.0 --service-role EMR_DefaultRole --ec2-attributes InstanceProfile=EMR_EC2_DefaultRole --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge 

**3. Create an Amazon EMR cluster with default roles**

- Command::

    aws emr create-cluster --ami-version 3.1.0 --use-default-roles --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**4. Create an Amazon EMR cluster with MASTER, CORE, and TASK instance groups**

- Command::

    aws emr create-cluster --ami-version 3.1.0 --auto-terminate --instance-groups Name=Master,InstanceGroupType=MASTER,InstanceType=m3.xlarge,InstanceCount=1 Name=Core,InstanceGroupType=CORE,InstanceType=m3.xlarge,InstanceCount=2 Name=Task,InstanceGroupType=TASK,InstanceType=m3.xlarge,InstanceCount=2

**5. Specify whether the cluster should terminate after completing all the steps**

- Create an Amazon EMR cluster that will terminate after completing all the steps::

    aws emr create-cluster --ami-version 3.1.0  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge  InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**6. Specify EC2 Attributes**

- Create an Amazon EMR cluster with Amazon EC2 Key Pair "myKey" and instance profile "myProfile"::

    aws emr create-cluster --ec2-attributes KeyName=myKey,InstanceProfile=myRole --ami-version 3.1.0  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Create an Amazon EMR cluster in an Amazon VPC subnet::

    aws emr create-cluster --ec2-attributes SubnetId=subnet-xxxxx --ami-version 3.1.0  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Create an Amazon EMR cluster in an AvailabilityZone. For example, us-east-1b::

    aws emr create-cluster --ec2-attributes AvailabilityZone=us-east-1b --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge

- Create an Amazon EMR cluster specifying the Amazon EC2 security groups::

	aws emr create-cluster --ami-version 3.3.1 --service-role EMR_DefaultRole --ec2-attributes InstanceProfile=myRole,EmrManagedMasterSecurityGroup=sg-master1,EmrManagedSlaveSecurityGroup=sg-slave1,AdditionalMasterSecurityGroups=[sg-addMaster1,sg-addMaster2,sg-addMaster3,sg-addMaster4],AdditionalSlaveSecurityGroups=[sg-addSlave1,sg-addSlave2,sg-addSlave3,sg-addSlave4] --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge

- Create an Amazon EMR cluster specifying only the EMR managed Amazon EC2 security groups::

	aws emr create-cluster --ami-version 3.3.1 --service-role EMR_DefaultRole --ec2-attributes InstanceProfile=myRole,EmrManagedMasterSecurityGroup=sg-master1,EmrManagedSlaveSecurityGroup=sg-slave1 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge

- Create an Amazon EMR cluster specifying only the additional Amazon EC2 security groups::

	aws emr create-cluster --ami-version 3.3.1 --service-role EMR_DefaultRole --ec2-attributes InstanceProfile=myRole,AdditionalMasterSecurityGroups=[sg-addMaster1,sg-addMaster2,sg-addMaster3,sg-addMaster4],AdditionalSlaveSecurityGroups=[sg-addSlave1,sg-addSlave2,sg-addSlave3,sg-addSlave4] --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge

- JSON equivalent (contents of ec2_attributes.json)::

    [
     {
       "SubnetId": "subnet-xxxxx",
       "KeyName": "myKey",
       "InstanceProfile":"myRole",
       "EmrManagedMasterSecurityGroup": "sg-master1",
       "EmrManagedSlaveSecurityGroup": "sg-slave1",
       "AdditionalMasterSecurityGroups": ["sg-addMaster1","sg-addMaster2","sg-addMaster3","sg-addMaster4"],
       "AdditionalSlaveSecurityGroups": ["sg-addSlave1","sg-addSlave2","sg-addSlave3","sg-addSlave4"]
     }
   ]

NOTE: JSON arguments must include options and values as their own items in the list.

- Command (using ec2_attributes.json)::

	aws emr create-cluster --ami-version 3.3.1 --service-role EMR_DefaultRole --ec2-attributes file://./ec2_attributes.json  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge

**7. Enable debugging and specify a Log URI**

- Command::

    aws emr create-cluster --enable-debugging --log-uri s3://myBucket/myLog  --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**8. Add tags when creating an Amazon EMR cluster**

- Add a list of tags::

    aws emr create-cluster --tags name="John Doe" age=29 address="123 East NW Seattle" --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- List tags of an Amazon EMR cluster::

    aws emr describe-cluster --cluster-id j-XXXXXXYY --query Cluster.Tags

**9. Add a list of bootstrap actions when creating an Amazon EMR Cluster**

- Command::

    aws emr create-cluster --bootstrap-actions Path=s3://mybucket/myscript1,Name=BootstrapAction1,Args=[arg1,arg2] Path=s3://mybucket/myscript2,Name=BootstrapAction2,Args=[arg1,arg2] --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- The following example changes the maximum number of map tasks and sets the NameNode heap size::

    aws emr create-cluster --bootstrap-actions Path=s3://elasticmapreduce/bootstrap-actions/configure-hadoop,Name="Change the maximum number of map tasks",Args=[--yarn-key-value,mapred.tasktracker.map.tasks.maximum=2] Path=s3://elasticmapreduce/bootstrap-actions/configure-daemons,Name="Set the NameNode heap size",Args=[--namenode-heap-size=2048,--namenode-opts=-XX:GCTimeRatio=19] --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge

**10. Create an Amazon EMR cluster with applications**

- Create an Amazon EMR cluster with Hive, Pig, HBase, Ganglia, and Impala installed::

    aws emr create-cluster --applications Name=Hive Name=Pig Name=HBase Name=Ganglia Name=Impala,Args=[IMPALA_BACKEND_PORT=22001,IMPALA_MEM_LIMIT=70%] --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate
  
- Create an Amazon EMR cluster with Hue, Hive, and Pig installed::

    aws emr create-cluster --ami-version=3.3.0 --applications Name=Hue Name=Hive Name=Pig --use-default-roles --ec2-attributes KeyName=myKey --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m1.large

- Create an Amazon EMR cluster with Hive and Pig installed::

    aws emr create-cluster --applications Name=Hive Name=Pig --ami-version 2.4.2 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Create an Amazon EMR cluster with MapR M7 edition::

    aws emr create-cluster --applications Name=MapR,Args=--edition,m7,--version,3.0.2 --ami-version 2.4.8 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**11. Restore HBase data from backup when creating an Amazon EMR cluster**

-Command::

    aws emr create-cluster --applications Name=HBase --restore-from-hbase-backup Dir=s3://myBucket/myBackup,BackupVersion=myBackupVersion --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**12. To add Custom JAR steps to a cluster when creating an Amazon EMR cluster**

- Command::

    aws emr create-cluster --steps Type=CUSTOM_JAR,Name=CustomJAR,ActionOnFailure=CONTINUE,Jar=s3://myBucket/mytest.jar,Args=arg1,arg2,arg3 Type=CUSTOM_JAR,Name=CustomJAR,ActionOnFailure=CONTINUE,Jar=s3://myBucket/mytest.jar,MainClass=mymainclass,Args=arg1,arg2,arg3  --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

- Custom JAR steps required parameters::

    Jar

- Custom JAR steps optional parameters::

    Type, Name, ActionOnFailure, Args

**13. To add Streaming steps when creating an Amazon EMR cluster**

- Command::

    aws emr create-cluster --steps Type=STREAMING,Name='Streaming Program',ActionOnFailure=CONTINUE,Args=[-files,s3://elasticmapreduce/samples/wordcount/wordSplitter.py,-mapper,wordSplitter.py,-reducer,aggregate,-input,s3://elasticmapreduce/samples/wordcount/input,-output,s3://mybucket/wordcount/output] --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

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

    aws emr create-cluster --steps file://./step.json --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**14. To use multiple files in a Streaming step (JSON only)**

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

    aws emr create-cluster --steps file://./multiplefiles.json --ami-version 3.3.1 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge --auto-terminate

**15. To add Hive steps when creating an Amazon EMR cluster**

- Command::

    aws emr create-cluster --steps Type=HIVE,Name='Hive program',ActionOnFailure=CONTINUE,ActionOnFailure=TERMINATE_CLUSTER,Args=[-f,s3://elasticmapreduce/samples/hive-ads/libs/model-build.q,-d,INPUT=s3://elasticmapreduce/samples/hive-ads/tables,-d,OUTPUT=s3://mybucket/hive-ads/output/2014-04-18/11-07-32,-d,LIBS=s3://elasticmapreduce/samples/hive-ads/libs] --applications Name=Hive --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge
      
- Hive steps required parameters::

    Type, Args

- Hive steps optional parameters::

    Name, ActionOnFailure

**16. To add Pig steps when creating an Amazon EMR cluster**

- Command::

    aws emr create-cluster --steps Type=PIG,Name='Pig program',ActionOnFailure=CONTINUE,Args=[-f,s3://elasticmapreduce/samples/pig-apache/do-reports2.pig,-p,INPUT=s3://elasticmapreduce/samples/pig-apache/input,-p,OUTPUT=s3://mybucket/pig-apache/output] --applications Name=Pig --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge

- Pig steps required parameters::

    Type, Args

- Pig steps optional parameters::

    Name, ActionOnFailure

**17. To add Impala steps when creating an Amazon EMR cluster**

- Command::

    aws emr create-cluster --steps Type=CUSTOM_JAR,Name='Wikipedia Impala program',ActionOnFailure=CONTINUE,Jar=s3://elasticmapreduce/libs/script-runner/script-runner.jar,Args="/home/hadoop/impala/examples/wikipedia/wikipedia-with-s3distcp.sh" Type=IMPALA,Name='Impala program',ActionOnFailure=CONTINUE,Args=-f,--impala-script,s3://myimpala/input,--console-output-path,s3://myimpala/output --applications Name=Impala --ami-version 3.1.0 --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge InstanceGroupType=CORE,InstanceCount=2,InstanceType=m3.xlarge 

- Impala steps required parameters::

    Type, Args

- Impala steps optional parameters::

    Name, ActionOnFailure


**18. To enable consistent view in EMRFS when creating an Amazon EMR cluster**

- Command::

    aws emr create-cluster --instance-type m3.xlarge --ami-version 3.4 --emrfs Consistent=true,RetryCount=5,RetryPeriod=30
 
- Required parameters::
    
    Consistent=true

- JSON equivalent (contents of emrfs.json)::
 
    {
      "Consistent": true,
      "RetryCount": 5,
      "RetryPeriod": 30
    }
 
- Command (Using emrfs.json)::
 
    aws emr create-cluster --instance-type m3.xlarge --ami-version 3.4 --emrfs file://emrfs.json


**19. To enable consistent view with arguments e.g. change the DynamoDB read and write capacity when creating an Amazon EMR cluster**

- Command::

    aws emr create-cluster --instance-type m3.xlarge --ami-version 3.4 --emrfs Consistent=true,RetryCount=5,RetryPeriod=30,Args=[fs.s3.consistent.metadata.read.capacity=600,fs.s3.consistent.metadata.write.capacity=300]

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
 
    aws emr create-cluster --instance-type m3.xlarge --ami-version 3.4 --emrfs file://emrfs.json

**20. To enable Amazon S3 server-side encryption in EMRFS when creating an Amazon EMR cluster**
 
- Command (Use Encryption=ServerSide)::

    aws emr create-cluster --instance-type m3.xlarge --ami-version 3.4 --emrfs Encryption=ServerSide
 
- Required parameters::
 
    Encryption=ServerSide
 
- Optional parameters::
 
    Args
 
- JSON equivalent (contents of emrfs.json)::
 
    {
      "Encryption": "ServerSide",
      "Args": ["fs.s3.serverSideEncryptionAlgorithm=AES256"]
    }
 
**21. To enable Amazon S3 client-side encryption using a key managed by AWS Key Management Service (KMS) in EMRFS when creating an Amazon EMR cluster**
 
- Command::
 
    aws emr create-cluster --instance-type m3.xlarge --ami-version 3.6.0 --emrfs Encryption=ClientSide,ProviderType=KMS,KMSKeyId=myKMSKeyId
 
- Required parameters::
 
    Encryption=ClientSide, ProviderType=KMS, KMSKeyId
 
- Optional parameters::
 
    Args
 
- JSON equivalent (contents of emrfs.json)::
 
    {
      "Encryption": "ClientSide",
      "ProviderType": "KMS",
      "KMSKeyId": "myKMSKeyId"
    }
 
**22. To enable Amazon S3 client-side encryption with a custom encryption provider in EMRFS when creating an Amazon EMR cluster**
 
- Command::
 
    aws emr create-cluster --instance-type m3.xlarge --ami-version 3.6.0 --emrfs Encryption=ClientSide,ProviderType=Custom,CustomProviderLocation=s3://mybucket/myfolder/provider.jar,CustomProviderClass=classname
 
- Required parameters::
 
    Encryption=ClientSide, ProviderType=Custom, CustomProviderLocation, CustomProviderClass
 
- Optional parameters::
 
    Args
 
- JSON equivalent (contents of emrfs.json)::
 
    {
      "Encryption": "ClientSide",
      "ProviderType": "Custom",
      "CustomProviderLocation": "s3://mybucket/myfolder/provider.jar",
      "CustomProviderClass": "classname"
    }

**23. To enable Amazon S3 client-side encryption with a custom encryption provider in EMRFS and passing arguments expected by the class**
 
- Command::

    aws emr create-cluster --ami-version 3.6.0 --instance-type m3.xlarge --instance-count 2 --emrfs Encryption=ClientSide,ProviderName=myProvider,CustomProviderLocation=s3://mybucket/myfolder/myprovider.jar,CustomProviderClass=classname --bootstrap-action Path=s3://elasticmapreduce/bootstrap-actions/configure-hadoop,Args=[-e,myProvider.arg1=value1,-e,myProvider.arg2=value2]
 
- Required parameters::
 
    Encryption=ClientSide, ProviderType=Custom, CustomProviderLocation, CustomProviderClass
 
- Optional parameters::
 
    Args (expected by CustomProviderClass, passed to emrfs-site.xml using configure-hadoop bootstrap action)
 
- JSON equivalent (contents of emrfs.json)::
 
    {
      "Encryption": "ClientSide",
      "ProviderType": "Custom",
      "CustomProviderLocation": "s3://mybucket/myfolder/provider.jar",
      "CustomProviderClass": "classname"
    }