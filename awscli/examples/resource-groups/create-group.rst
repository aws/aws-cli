**To create a tag-based resource group**

This example creates a tag-based resource group of Amazon EC2 instances in the current region that are tagged with a tag key of Name, and a tag key value of WebServers. The group name is WebServer3.

Command::

  aws resource-groups create-group --name WebServer3 --resource-query '{"Type":"TAG_FILTERS_1_0", "Query":"{\"ResourceTypeFilters\":[\"AWS::EC2::Instance\"],\"TagFilters\":[{\"Key\":\"Name\", \"Values\":[\"WebServers\"]}]}"}'

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

**To create a CloudFormation stack-based resource group**

This example creates an AWS CloudFormation stack-based resource group named sampleCFNstackgroup. The query allows all resources that are in the CloudFormation stack that are supported by AWS Resource Groups.

Command::

  aws resource-groups create-group --name sampleCFNstackgroup --resource-query '{"Type": "CLOUDFORMATION_STACK_1_0", "Query": "{\"ResourceTypeFilters\":[\"AWS::AllSupported\"],\"StackIdentifier\":\"arn:aws:cloudformation:us-east-2:123456789012:stack/testcloudformationstack/1415z9z0-z39z-11z8-97z5-500z212zz6fz\"}"}'

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

