**1. To add Custom JAR steps to a cluster**

- Command::

    aws emr add-steps --cluster-id j-XXXXXXXX --steps Type=CUSTOM_JAR,Name=CustomJAR,ActionOnFailure=CONTINUE,Jar=s3://mybucket/mytest.jar,Args=arg1,arg2,arg3 Type=CUSTOM_JAR,Name=CustomJAR,ActionOnFailure=CONTINUE,Jar=s3://mybucket/mytest.jar,MainClass=mymainclass,Args=arg1,arg2,arg3

- Required parameters::

    Jar

- Optional parameters::

    Type, Name, ActionOnFailure, Args

- Output::

    {
        "StepIds":[
            "s-XXXXXXXX",
            "s-YYYYYYYY"
        ]
    }

**2. To add Streaming steps to a cluster**

- Command::
 
    aws emr add-steps --cluster-id j-XXXXXXXX --steps Type=STREAMING,Name='Streaming Program',ActionOnFailure=CONTINUE,Args=-mapper,mymapper,-reducer,myreducer,-input,myinput,-output,myoutput Type=STREAMING,Name='Streaming Program',ActionOnFailure=CONTINUE,Args=--files,s3://elasticmapreduce/samples/wordcount/wordSplitter.py,-mapper,wordSplitter.py,-reducer,aggregate,-input,s3://elasticmapreduce/samples/wordcount/input,-output,s3://mybucket/wordcount/output

- Required parameters::

    Type, Args

- Optional parameters::

    Name, ActionOnFailure

- Output::

    {
        "StepIds":[
            "s-XXXXXXXX",
            "s-YYYYYYYY"
        ]
    }


**3. To add Hive steps to a cluster**

- Command::

    aws emr add-steps --cluster-id j-XXXXXXXX --steps Type=HIVE,Name='Hive program',ActionOnFailure=CONTINUE,Version=latest,Args=[-f,s3://mybuckey/myhivescript.q,-d,INPUT=s3://mybucket/myhiveinput,-d,OUTPUT=s3://mybucket/myhiveoutput,arg1,arg2] Type=HIVE,Name='Hive steps',ActionOnFailure=TERMINATE_CLUSTER,Version=latest,Args=[-f,s3://elasticmapreduce/samples/hive-ads/libs/model-build.q,-d,INPUT=s3://elasticmapreduce/samples/hive-ads/tables,-d,OUTPUT=s3://mybucket/hive-ads/output/2014-04-18/11-07-32,-d,LIBS=s3://elasticmapreduce/samples/hive-ads/libs]


- Required parameters::

    Type, Args

- Optional parameters::

    Name, ActionOnFailure, Version

- Output::

    {
        "StepIds":[
            "s-XXXXXXXX",
            "s-YYYYYYYY"
        ]
    }


**4. To add Pig steps to a cluster**

- Command::

    aws emr add-steps --cluster-id j-XXXXXXXX --steps Type=PIG,Name='Pig program',ActionOnFailure=CONTINUE,Version=latest,Args=[-f,s3://mybuckey/mypigscript.pig,-p,INPUT=s3://mybucket/mypiginput,-p,OUTPUT=s3://mybucket/mypigoutput,arg1,arg2] Type=PIG,Name='Pig program',Version=latest,Args=[-f,s3://elasticmapreduce/samples/pig-apache/do-reports2.pig,-p,INPUT=s3://elasticmapreduce/samples/pig-apache/input,-p,OUTPUT=s3://mybucket/pig-apache/output,arg1,arg2]


- Required parameters::

    Type, Args

- Optional parameters::

    Name, ActionOnFailure, Version

- Output::

    {
        "StepIds":[
            "s-XXXXXXXX",
            "s-YYYYYYYY"
        ]
    }


**5. To add Impala steps to a cluster**

- Command::

    aws emr add-steps --cluster-id j-XXXXXXXX --steps Type=IMPALA,Name='Impala program',ActionOnFailure=CONTINUE,Args=-f,--impala-script,s3://myimpala/input,--console-output-path,s3://myimpala/output Type=IMPALA,Name='Impala program',ActionOnFailure=CONTINUE,Args=-f,--impala-script,s3://myimpala/input,--console-output-path,s3://myimpala/output

- Required parameters::

    Type, Args

- Optional parameters::

    Name, ActionOnFailure

- Output::

    {
        "StepIds":[
            "s-XXXXXXXX",
            "s-YYYYYYYY"
        ]
    }

