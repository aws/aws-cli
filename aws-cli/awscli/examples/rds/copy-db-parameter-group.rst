**To copy a DB cluster parameter group**

The following ``copy-db-parameter-group`` example makes a copy of a DB parameter group. :: 

    aws rds copy-db-parameter-group \
        --source-db-parameter-group-identifier mydbpg \
        --target-db-parameter-group-identifier mydbpgcopy \
        --target-db-parameter-group-description "Copy of mydbpg parameter group"

Output::

    {
        "DBParameterGroup": {
            "DBParameterGroupName": "mydbpgcopy",
            "DBParameterGroupArn": "arn:aws:rds:us-west-2:123456789012:pg:mydbpgcopy",
            "DBParameterGroupFamily": "mysql5.7",
            "Description": "Copy of mydbpg parameter group"
        }
    }

For more information, see `Copying a DB Parameter Group <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithParamGroups.Copying.html>`__ in the *Amazon RDS Users Guide*.
