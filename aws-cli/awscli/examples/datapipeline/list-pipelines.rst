**To list your pipelines**

The following ``list-pipelines`` example lists your pipelines. ::

    aws datapipeline list-pipelines

Output::

    {
        "pipelineIdList": [
            {
                "id": "df-00627471SOVYZEXAMPLE",
                "name": "my-pipeline"
            },
            {
                "id": "df-09028963KNVMREXAMPLE",
                "name": "ImportDDB"
            },
            {
                "id": "df-0870198233ZYVEXAMPLE",
                "name": "CrossRegionDDB"
            },
            {
                "id": "df-00189603TB4MZEXAMPLE",
                "name": "CopyRedshift"
            }
        ]
    }

For more information, see `Viewing Your Pipelines <https://docs.aws.amazon.com/datapipeline/latest/DeveloperGuide/dp-list-pipelines.html>`__ in the *AWS Data Pipeline Developer Guide*.
