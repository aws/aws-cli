**To disable a transition to a stage in a pipeline**

The following ``disable-stage-transition`` example disables transitions into the Beta stage of the MyFirstPipeline pipeline in AWS CodePipeline. ::

    aws codepipeline disable-stage-transition \
        --pipeline-name MyFirstPipeline \
        --stage-name Beta  \
        --transition-type Inbound \
        --reason "An example reason"

This command produces no output.

For more information, see `Working with stage transitions in CodePipeline <https://docs.aws.amazon.com/codepipeline/latest/userguide/transitions.html>`__ in the *AWS CodePipeline User Guide*.
