**To enable a transition to a stage in a pipeline**

The following ``enable-stage-transition`` example enables transitions into the Beta stage of the MyFirstPipeline pipeline in AWS CodePipeline. ::

    aws codepipeline enable-stage-transition --pipeline-name MyFirstPipeline --stage-name Beta  --transition-type Inbound


Output::

    None.