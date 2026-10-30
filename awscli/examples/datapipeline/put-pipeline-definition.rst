**To upload a pipeline definition**

The following ``put-pipeline-definition`` example uploads the specified pipeline definition to the specified pipeline. ::

    aws datapipeline put-pipeline-definition \
        --pipeline-id df-00627471SOVYZEXAMPLE \
        --pipeline-definition file://my-pipeline-definition.json

Contents of ``my-pipeline-definition.json``::

    {
        "parameters": [
            {
                "type": "AWS::S3::ObjectKey",
                "id": "myS3OutputLoc",
                "description": "S3 output folder"
            },
            {
                "default": "s3://amzn-s3-demo-bucket/pig-apache-logs/data",
                "type": "AWS::S3::ObjectKey",
                "id": "myS3InputLoc",
                "description": "S3 input folder"
            },
            {
                "default": "grep -rc \"GET\" ${INPUT1_STAGING_DIR}/* > ${OUTPUT1_STAGING_DIR}/output.txt",
                "type": "String",
                "id": "myShellCmd",
                "description": "Shell command to run"
            }
        ],
        "objects": [
            {
                "type": "Ec2Resource",
                "terminateAfter": "20 Minutes",
                "instanceType": "t1.micro",
                "id": "EC2ResourceObj",
                "name": "EC2ResourceObj"
            },
            {
                "name": "Default",
                "failureAndRerunMode": "CASCADE",
                "resourceRole": "DataPipelineDefaultResourceRole",
                "schedule": {
                    "ref": "DefaultSchedule"
                },
                "role": "DataPipelineDefaultRole",
                "scheduleType": "cron",
                "id": "Default"
            },
            {
                "directoryPath": "#{myS3OutputLoc}/#{format(@scheduledStartTime, 'YYYY-MM-dd-HH-mm-ss')}",
                "type": "S3DataNode",
                "id": "S3OutputLocation",
                "name": "S3OutputLocation"
            },
            {
                "directoryPath": "#{myS3InputLoc}",
                "type": "S3DataNode",
                "id": "S3InputLocation",
                "name": "S3InputLocation"
            },
            {
                "startAt": "FIRST_ACTIVATION_DATE_TIME",
                "name": "Every 15 minutes",
                "period": "15 minutes",
                "occurrences": "4",
                "type": "Schedule",
                "id": "DefaultSchedule"
            },
            {
                "name": "ShellCommandActivityObj",
                "command": "#{myShellCmd}",
                "output": {
                    "ref": "S3OutputLocation"
                },
                "input": {
                    "ref": "S3InputLocation"
                },
                "stage": "true",
                "type": "ShellCommandActivity",
                "id": "ShellCommandActivityObj",
                "runsOn": {
                    "ref": "EC2ResourceObj"
                }
            }
        ],
        "values": {
            "myS3OutputLoc": "s3://amzn-s3-demo-bucket/",
            "myS3InputLoc": "s3://amzn-s3-demo-bucket/pig-apache-logs/data",
            "myShellCmd": "grep -rc \"GET\" ${INPUT1_STAGING_DIR}/* > ${OUTPUT1_STAGING_DIR}/output.txt"
        }
    }
   
Output::

    {
        "validationErrors": [],
        "errored": false,
        "validationWarnings": []
    }

For more information, see `Pipeline definition file syntax <https://docs.aws.amazon.com/datapipeline/latest/DeveloperGuide/dp-writing-pipeline-definition.html>`__ in the *AWS Data Pipeline Developer Guide*.
