**To describe your pipelines**

The following ``describe-pipelines`` example describes the specified pipeline. ::

    aws datapipeline describe-pipelines \
        --pipeline-ids df-00627471SOVYZEXAMPLE
   
Output::

    {
        "pipelineDescriptionList": [
            {
                "fields": [
                    {
                        "stringValue": "PENDING",
                        "key": "@pipelineState"
                    },
                    {
                        "stringValue": "my-pipeline",
                        "key": "name"
                    },
                    {
                        "stringValue": "2015-04-07T16:05:58",
                        "key": "@creationTime"
                    },
                    {
                        "stringValue": "df-00627471SOVYZEXAMPLE",
                        "key": "@id"
                    },
                    {
                        "stringValue": "123456789012",
                        "key": "pipelineCreator"
                    },
                    {
                        "stringValue": "PIPELINE",
                        "key": "@sphere"
                    },
                    {
                        "stringValue": "123456789012",
                        "key": "@userId"
                    },
                    {
                        "stringValue": "123456789012",
                        "key": "@accountId"
                    },
                    {
                        "stringValue": "my-pipeline-token",
                        "key": "uniqueId"
                    }
                ],
                "pipelineId": "df-00627471SOVYZEXAMPLE",
                "name": "my-pipeline",
                "tags": []
            }
        ]
    }

For more information, see `Working with pipelines <https://docs.aws.amazon.com/datapipeline/latest/DeveloperGuide/dp-managing-pipeline.html>`__ in the *AWS Data Pipeline Developer Guide*.
