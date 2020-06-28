**To query specific attempts**

This example queries the attempts in a pipeline using dates and the scheduledStartTime field::

aws datapipeline query-objects --pipeline-id df-00627471SOVYZEXAMPLE --sphere ATTEMPT --output text --query ids --objects-query '{"selectors":[{"fieldName":"@scheduledStartTime", "operator":{"type":"BETWEEN","values":["2020-04-08T15:25:51","2020-04-08T17:25:51"]}}]}'