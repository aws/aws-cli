**To update the query for a tag-based resource group**

This example updates the query for a tag-based resource group of Amazon EC2 instances. To update the group query, you can change the values specified for ResourceTypeFilters or TagFilters.

Command::

  aws resource-groups update-group-query --group-name WebServer3 --resource-query '{"Type":"TAG_FILTERS_1_0", "Query":"{\"ResourceTypeFilters\":[\"AWS::EC2::Instance\"],\"TagFilters\":[{\"Key\":\"Name\", \"Values\":[\"WebServers\"]}]}"}'

Output::

  {
    "Group": {
        "GroupArn": "arn:aws:resource-groups:us-east-2:000000000000:group/WebServer3",
        "Name": "WebServer3"
    },
    "ResourceQuery": {
        "Type": "TAG_FILTERS_1_0",
        "Query": "{\"ResourceTypeFilters\":[\"AWS::EC2::Instance\"],\"TagFilters\":[{\"Key\":\"Name\", \"Values\":[\"WebServers\"]}]}"
    }
}

**To update the query for a CloudFormation stack-based resource group**

This example updates the query for an AWS CloudFormation stack-based resource group named sampleCFNstackgroup. To update the group query, you can change the values specified for ResourceTypeFilters or StackIdentifier.

Command::

  aws resource-groups update-group-query --group-name sampleCFNstackgroup --resource-query '{"Type": "CLOUDFORMATION_STACK_1_0", "Query": "{\"ResourceTypeFilters\":[\"AWS::AllSupported\"],\"StackIdentifier\":\"arn:aws:cloudformation:us-east-2:123456789012:stack/testcloudformationstack/1415z9z0-z39z-11z8-97z5-500z212zz6fz\"}"}'

Output::

  {
    "Group": {
        "GroupArn": "arn:aws:resource-groups:us-east-2:123456789012:group/sampleCFNstackgroup",
        "Name": "sampleCFNstackgroup"
    },
    "ResourceQuery": {
        "Type": "CLOUDFORMATION_STACK_1_0",
        "Query":'{\"CloudFormationStackArn\":\"arn:aws:cloudformation:us-east-2:123456789012:stack/testcloudformationstack/1415z9z0-z39z-11z8-97z5-500z212zz6fz\",\"ResourceTypeFilters\":[\"AWS::AllSupported\"]}"}'
    }
}

