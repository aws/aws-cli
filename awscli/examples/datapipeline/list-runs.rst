**To list your pipeline runs**

This example lists the runs for the specified pipeline::

   aws datapipeline list-runs --pipeline-id df-00627471SOVYZEXAMPLE
   
The following is example output::

       Name                       Scheduled Start        Status                     ID                                              Started                Ended
   -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
   1.  EC2ResourceObj             2015-04-12T17:33:02    CREATING                   @EC2ResourceObj_2015-04-12T17:33:02             2015-04-12T17:33:10

   2.  S3InputLocation            2015-04-12T17:33:02    FINISHED                   @S3InputLocation_2015-04-12T17:33:02            2015-04-12T17:33:09    2015-04-12T17:33:09

   3.  S3OutputLocation           2015-04-12T17:33:02    WAITING_ON_DEPENDENCIES    @S3OutputLocation_2015-04-12T17:33:02           2015-04-12T17:33:09

   4.  ShellCommandActivityObj    2015-04-12T17:33:02    WAITING_FOR_RUNNER         @ShellCommandActivityObj_2015-04-12T17:33:02    2015-04-12T17:33:09
