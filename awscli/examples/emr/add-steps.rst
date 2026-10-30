**Example 1: To add Custom JAR steps to a cluster**

The following ``add-steps`` example adds two Custom JAR steps to the specified cluster. ::

    aws emr add-steps \
        --cluster-id j-XXXXXXXX \
        --steps Type=CUSTOM_JAR,Name=CustomJAR,ActionOnFailure=CONTINUE,Jar=s3://amzn-s3-demo-bucket/mytest.jar,Args=arg1,arg2,arg3 Type=CUSTOM_JAR,Name=CustomJAR,ActionOnFailure=CONTINUE,Jar=s3://amzn-s3-demo-bucket/mytest.jar,MainClass=mymainclass,Args=arg1,arg2,arg3

- Required parameters::

    Jar

- Optional parameters::

    Type, Name, ActionOnFailure, Args

Output::

    {
        "StepIds":[
            "s-XXXXXXXX",
            "s-YYYYYYYY"
        ]
    }

**Example 2: To add Streaming steps to a cluster**

The following ``add-steps`` example adds a Streaming step to the specified cluster. ::

    aws emr add-steps \
        --cluster-id j-XXXXXXXX \
        --steps Type=STREAMING,Name='Streaming Program',ActionOnFailure=CONTINUE,Args=[-files,s3://elasticmapreduce/samples/wordcount/wordSplitter.py,-mapper,wordSplitter.py,-reducer,aggregate,-input,s3://elasticmapreduce/samples/wordcount/input,-output,s3://amzn-s3-demo-bucket/wordcount/output]

- Required parameters::

    Type, Args

- Optional parameters::

    Name, ActionOnFailure

The following ``add-steps`` example adds the Streaming step that is defined in the ``step.json`` file. ::

    aws emr add-steps \
        --cluster-id j-XXXXXXXX \
        --steps file://./step.json

Contents of ``step.json``::

    [
        {
            "Name": "JSON Streaming Step",
            "Args": ["-files","s3://elasticmapreduce/samples/wordcount/wordSplitter.py","-mapper","wordSplitter.py","-reducer","aggregate","-input","s3://elasticmapreduce/samples/wordcount/input","-output","s3://amzn-s3-demo-bucket/wordcount/output"],
            "ActionOnFailure": "CONTINUE",
            "Type": "STREAMING"
        }
    ]

NOTE: JSON arguments must include options and values as their own items in the list.

Output::

    {
        "StepIds":[
            "s-XXXXXXXX",
            "s-YYYYYYYY"
        ]
    }

**Example 3: To add a Streaming step with multiple files to a cluster (JSON only)**

The following ``add-steps`` example adds a Streaming step with multiple files to the specified cluster. The step is defined in the ``multiplefiles.json`` file.

The following command adds the step that is defined in the ``multiplefiles.json`` file. ::

    aws emr add-steps \
        --cluster-id j-XXXXXXXX \
        --steps file://./multiplefiles.json

Contents of ``multiplefiles.json``::

    [
        {
            "Name": "JSON Streaming Step",
            "Type": "STREAMING",
            "ActionOnFailure": "CONTINUE",
            "Args": [
                "-files",
                "s3://amzn-s3-demo-bucket/mapper.py,s3://amzn-s3-demo-bucket/reducer.py",
                "-mapper",
                "mapper.py",
                "-reducer",
                "reducer.py",
                "-input",
                "s3://amzn-s3-demo-bucket/input",
                "-output",
                "s3://amzn-s3-demo-bucket/output"
            ]
        }
    ]

- Required parameters::

    Type, Args

- Optional parameters::

    Name, ActionOnFailure

Output::

    {
        "StepIds":[
            "s-XXXXXXXX"
        ]
    }


**Example 4: To add Hive steps to a cluster**

The following ``add-steps`` example adds two Hive steps to the specified cluster. ::

    aws emr add-steps \
        --cluster-id j-XXXXXXXX \
        --steps Type=HIVE,Name='Hive program',ActionOnFailure=CONTINUE,Args=[-f,s3://amzn-s3-demo-bucket/myhivescript.q,-d,INPUT=s3://amzn-s3-demo-bucket/myhiveinput,-d,OUTPUT=s3://amzn-s3-demo-bucket/myhiveoutput,arg1,arg2] Type=HIVE,Name='Hive steps',ActionOnFailure=TERMINATE_CLUSTER,Args=[-f,s3://elasticmapreduce/samples/hive-ads/libs/model-build.q,-d,INPUT=s3://elasticmapreduce/samples/hive-ads/tables,-d,OUTPUT=s3://amzn-s3-demo-bucket/hive-ads/output/2014-04-18/11-07-32,-d,LIBS=s3://elasticmapreduce/samples/hive-ads/libs]


- Required parameters::

    Type, Args

- Optional parameters::

    Name, ActionOnFailure

Output::

    {
        "StepIds":[
            "s-XXXXXXXX",
            "s-YYYYYYYY"
        ]
    }


**Example 5: To add Pig steps to a cluster**

The following ``add-steps`` example adds two Pig steps to the specified cluster. ::

    aws emr add-steps \
        --cluster-id j-XXXXXXXX \
        --steps Type=PIG,Name='Pig program',ActionOnFailure=CONTINUE,Args=[-f,s3://amzn-s3-demo-bucket/mypigscript.pig,-p,INPUT=s3://amzn-s3-demo-bucket/mypiginput,-p,OUTPUT=s3://amzn-s3-demo-bucket/mypigoutput,arg1,arg2] Type=PIG,Name='Pig program',Args=[-f,s3://elasticmapreduce/samples/pig-apache/do-reports2.pig,-p,INPUT=s3://elasticmapreduce/samples/pig-apache/input,-p,OUTPUT=s3://amzn-s3-demo-bucket/pig-apache/output,arg1,arg2]


- Required parameters::

    Type, Args

- Optional parameters::

    Name, ActionOnFailure

Output::

    {
        "StepIds":[
            "s-XXXXXXXX",
            "s-YYYYYYYY"
        ]
    }


**Example 6: To add Impala steps to a cluster**

The following ``add-steps`` example adds an Impala step to the specified cluster. ::

    aws emr add-steps \
        --cluster-id j-XXXXXXXX \
        --steps Type=IMPALA,Name='Impala program',ActionOnFailure=CONTINUE,Args=--impala-script,s3://amzn-s3-demo-bucket/input,--console-output-path,s3://amzn-s3-demo-bucket/output

- Required parameters::

    Type, Args

- Optional parameters::

    Name, ActionOnFailure

Output::

    {
        "StepIds":[
            "s-XXXXXXXX",
            "s-YYYYYYYY"
        ]
    }

For more information, see `Submit work to an Amazon EMR cluster <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-work-with-steps.html>`__ in the *Amazon EMR Management Guide*.
