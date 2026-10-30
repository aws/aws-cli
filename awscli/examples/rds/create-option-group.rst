**To Create an Amazon RDS option group**

The following ``create-option-group`` example creates a new Amazon RDS option group named ``MyOptionGroup`` with a description for ``Oracle Enterprise Edition`` version ``11.2``. ::

    aws rds create-option-group \
        --option-group-name MyOptionGroup \
        --engine-name oracle-ee \
        --major-engine-version 11.2 \
        --option-group-description "Oracle Database Manager Database Control" 

Output::

    {
        "OptionGroup": {
            "OptionGroupName": "myoptiongroup",
            "OptionGroupDescription": "Oracle Database Manager Database Control",
            "EngineName": "oracle-ee",
            "MajorEngineVersion": "11.2",
            "Options": [],
            "AllowsVpcAndNonVpcInstanceMemberships": true,
            "OptionGroupArn": "arn:aws:rds:us-west-2:123456789012:og:myoptiongroup"
        }
    }

For more information, see `Creating an option group <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithOptionGroups.html#USER_WorkingWithOptionGroups.Create>`__ in the *Amazon RDS User Guide*.
