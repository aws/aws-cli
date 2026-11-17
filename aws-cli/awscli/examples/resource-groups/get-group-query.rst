**To get the query attached to a resource group**

The following ``get-group-query`` example displays query attached to the specified resource group. ::

    aws resource-groups get-group-query \
        --group-name tbq-WebServer

Output::

    {
        "GroupQuery": {
            "GroupName": "tbq-WebServer",
            "ResourceQuery": {
                "Type": "TAG_FILTERS_1_0",
                "Query": "{\"ResourceTypeFilters\":[\"AWS::EC2::Instance\"],\"TagFilters\":[{\"Key\":\"Name\", \"Values\":[\"WebServers\"]}]}"
            }
        }
    }

For more information, see `Creating query-based groups in AWS Resource Groups <https://docs.aws.amazon.com/ARG/latest/userguide/gettingstarted-query.html>`__ in the *AWS Resource Groups User Guide*.
