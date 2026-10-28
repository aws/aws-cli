**To disable a transition to a stage in a pipeline**

The following ``disable-stage-transition`` example disables transitions into the Beta stage of the MyFirstPipeline pipeline in AWS CodePipeline. This command produces no output. ::

    aws codepipeline disable-stage-transition \
        --pipeline-name MyFirstPipeline \
        --stage-name Beta  \
        --transition-type Inbound \
        --reason "An example reason"
