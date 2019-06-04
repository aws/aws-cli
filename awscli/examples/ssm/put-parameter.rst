**Example 1: To change a parameter value**

The following ``put-parameter`` example changes the value of a parameter. ::

    aws ssm put-parameter \
        --name "welcome" \
        --type "String" \
        --value "good day sunshine" \
        --overwrite

Output::

    {
        "Version": 2
    }

For more information, see `About Parameters <https://docs.aws.amazon.com/systems-manager/latest/userguide/parameter-store-about-examples.html>`__ in the *AWS Systems Manager User Guide*.

**Example 2: To create an advanced parameter**

The following ``put-parameter`` example creates an advanced parameter. ::

    aws ssm put-parameter \
        --name "advanced-parameter" \
        --value "This is an advanced parameter" \
        --type "String" \
        --tier Advanced

Output::

    {
        "Version": 1
    }

For more information, see `About Advanced Parameters <https://docs.aws.amazon.com/systems-manager/latest/userguide/parameter-store-advanced-parameters.html>`__ in the *AWS Systems Manager User Guide*.

**Example 3: To convert a standard parameter to an advanced parameter**

The following ``put-parameter`` example converts a existing standard parameter into an advanced parameter. ::

    aws ssm put-parameter \
        --name "convert" \
        --value "Test" \
        --type "String" \
        --tier Advanced \
        --overwrite

Output::

    {
        "Version": 2
    }

For more information, see `About Advanced Parameters <https://docs.aws.amazon.com/systems-manager/latest/userguide/parameter-store-advanced-parameters.html>`__ in the *AWS Systems Manager User Guide*.

**Example 4: To create a parameter with a policy attached**

The following ``put-parameter`` example creates an advanced parameter with a parameter policy attached.  ::

    aws ssm put-parameter \
        --name "/Finance/Payroll/elixir3131" \
        --value "P@sSwW)rd" \
        --type "SecureString" \
        --tier Advanced \
        --policies "[{\"Type\":\"Expiration\",\"Version\":\"1.0\",\"Attributes\":{\"Timestamp\":\"2019-05-13T00:00:00.000Z\"}},{\"Type\":\"ExpirationNotification\",\"Version\":\"1.0\",\"Attributes\":{\"Before\":\"5\",\"Unit\":\"Days\"}},{\"Type\":\"NoChangeNotification\",\"Version\":\"1.0\",\"Attributes\":{\"After\":\"60\",\"Unit\":\"Days\"}}]"

Output::

    {
        "Version": 1
    }

For more information, see `Working with Parameter Policies <https://docs.aws.amazon.com/systems-manager/latest/userguide/parameter-store-policies.html>`__ in the *AWS Systems Manager User Guide*.

**Example 5: To add a policy to an existing parameter**

The following ``put-parameter`` example attaches a policy to an existing advanced parameter.  ::

    aws ssm put-parameter \
        --name "/Finance/Payroll/elixir3131" \
        --value "N3wP@sSwW)rd" \
        --type "SecureString" \
        --tier Advanced \
        --policies "[{\"Type\":\"Expiration\",\"Version\":\"1.0\",\"Attributes\":{\"Timestamp\":\"2019-05-13T00:00:00.000Z\"}},{\"Type\":\"ExpirationNotification\",\"Version\":\"1.0\",\"Attributes\":{\"Before\":\"5\",\"Unit\":\"Days\"}},{\"Type\":\"NoChangeNotification\",\"Version\":\"1.0\",\"Attributes\":{\"After\":\"60\",\"Unit\":\"Days\"}}]" 
        --overwrite

Output::

    {
        "Version": 2
    }

For more information, see `Working with Parameter Policies <https://docs.aws.amazon.com/systems-manager/latest/userguide/parameter-store-policies.html>`__ in the *AWS Systems Manager User Guide*.
