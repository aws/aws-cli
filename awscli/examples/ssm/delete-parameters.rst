**To delete a list of parameters**

The following ``delete-parameters`` example deletes the specified parameters. ::

    aws ssm delete-parameters \
        --names "MyFirstParameter" "MySecondParameter" "MyInvalidParameterName"

Output::

    {
        "DeletedParameters": [
            "MyFirstParameter",
            "MySecondParameter"
        ],
        "InvalidParameters": [
            "MyInvalidParameterName"
        ]
    }

For more information, see `Working with Parameters <https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-working.html>`_ in the *AWS Systems Manager User Guide*.
