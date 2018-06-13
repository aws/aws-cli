Modify a Parameter in a Parameter Group
---------------------------------------

This example shows how to modify the *wlm_json_configuration* parameter for workload management.

Command::
   aws redshift modify-cluster-parameter-group --parameter-group-name myclusterparametergroup --parameters '{"ParameterName":"wlm_json_configuration","ParameterValue":"[{\"user_group\":[\"example_user_group1\"],\"query_group\":[\"example_query_group1\"],\"query_concurrency\":7},{\"query_concurrency\":5}]"}'

Result::

    {
       "ParameterGroupStatus": "Your parameter group has been updated but changes won't get applied until you reboot the associated Clusters.",
       "ParameterGroupName": "myclusterparametergroup",
       "ResponseMetadata": {
          "RequestId": "09974cc0-64cd-11e2-bea9-49e0ce183f07"
       }
    }

