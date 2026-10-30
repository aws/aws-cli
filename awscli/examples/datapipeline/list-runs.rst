**Example 1: To list your pipeline runs**

The following ``list-runs`` example lists the runs for the specified pipeline. ::

    aws datapipeline list-runs \
        --pipeline-id df-00627471SOVYZEXAMPLE

Output::

        Name                       Scheduled Start        Status                     ID                                              Started                Ended
        -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    1.  EC2ResourceObj             2015-04-12T17:33:02    CREATING                   @EC2ResourceObj_2015-04-12T17:33:02             2015-04-12T17:33:10
    2.  S3InputLocation            2015-04-12T17:33:02    FINISHED                   @S3InputLocation_2015-04-12T17:33:02            2015-04-12T17:33:09    2015-04-12T17:33:09
    3.  S3OutputLocation           2015-04-12T17:33:02    WAITING_ON_DEPENDENCIES    @S3OutputLocation_2015-04-12T17:33:02           2015-04-12T17:33:09
    4.  ShellCommandActivityObj    2015-04-12T17:33:02    WAITING_FOR_RUNNER         @ShellCommandActivityObj_2015-04-12T17:33:02    2015-04-12T17:33:09

For more information, see `Interpreting Pipeline Status Details <https://docs.aws.amazon.com/datapipeline/latest/DeveloperGuide/dp-pipeline-status.html>`__ in the *AWS Data Pipeline Developer Guide*.

**Example 2: To list the pipeline runs between the specified dates**

The following ``list-runs`` example uses the ``--start-interval`` to specify the dates to include in the output. ::

    aws datapipeline list-runs \
        --pipeline-id df-01434553B58A2SHZUKO5 \
        --start-interval 2017-10-07T00:00:00,2017-10-08T00:00:00

Output::

            Name                                                Scheduled Start      Status
            ID                                                  Started              Ended
    ----------------------------------------------------------------------------------------------------
        1.  EC2ResourceObj                                      2017-10-07T09:00:00  FINISHED
            @EC2ResourceObj_2017-10-07T09:00:00                 2017-10-07T09:00:05  2017-10-07T09:12:45

        2.  S3InputLocation                                     2017-10-07T09:00:00  FINISHED
            @S3InputLocation_2017-10-07T09:00:00                2017-10-07T09:01:10  2017-10-07T09:01:10

        3.  S3OutputLocation                                    2017-10-07T09:00:00  FINISHED
            @S3OutputLocation_2017-10-07T09:00:00               2017-10-07T09:01:10  2017-10-07T09:10:52

        4.  ShellCommandActivityObj                             2017-10-07T09:00:00  FINISHED
            @ShellCommandActivityObj_2017-10-07T09:00:00        2017-10-07T09:01:10  2017-10-07T09:10:52

For more information, see `Viewing Pipeline Instance Details <https://docs.aws.amazon.com/datapipeline/latest/DeveloperGuide/dp-manage-pipeline-details-console.html>`__ in the *AWS Data Pipeline Developer Guide*.
