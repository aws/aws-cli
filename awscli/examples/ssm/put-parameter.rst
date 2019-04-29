**To create a parameter that uses a String data type**

This example creates a parameter.

Command::

  aws ssm put-parameter --name "welcome" --type "String" --value "helloWorld"
  
Output::

  {
    "Version": 1
  }

**To create a Secure String parameter**

This example creates a Secure String parameter. Singles quotes are used so that the literal value is passed.

Command::

  aws ssm put-parameter --name 'password' --type "SecureString" --value 'a value, for example P@ssW%rd#1'

**To create a parameter with an allowed pattern**

This example creates a String parameter and the values for this parameter are restricted to numbers.

Command::

  aws ssm put-parameter --name "NumbersOnly" --type "String" --value "10" --allowed-pattern "^\d+$"
  
**To change a parameter value**

This example changes the value of a parameter.

Command::

  aws ssm put-parameter --name "welcome" --type "String" --value "good day sunshine" --overwrite
  
Output::

  {
    "Version": 2
  }

**To create an advanced parameter**

This example creates an advanced parameter. For more information, see `About Systems Manager Advanced Parameters`_ in the *AWS Systems Manager User Guide*.

.. _`About Systems Manager Advanced Parameters`: https://docs.aws.amazon.com/systems-manager/latest/userguide/parameter-store-advanced-parameters.html

Command::

  aws ssm put-parameter --name "advanced-parameter" --value "This is an advanced parameter" --type "String" --tier Advanced
  
Output::

  {
    "Version": 1
  }

**To convert a standard parameter to an advanced parameter**

This example converts a standard parameter to an advanced parameter.

Command::

  aws ssm put-parameter --name "convert" --value "Test" --type "String" --tier Advanced --overwrite
  
Output::

  {
    "Version": 2
  }

**To create a parameter with a policy attached**

This example creates an advanced parameter with a parameter policy attached. For more information, see `Working with Parameter Policies`_ in the *AWS Systems Manager User Guide*.

.. _`Working with Parameter Policies`: https://docs.aws.amazon.com/systems-manager/latest/userguide/parameter-store-policies.html

Command::

  aws ssm put-parameter --name "/Finance/Payroll/elixir3131" --value "P@sSwW)rd" --type "SecureString" --tier Advanced --policies "[{\"Type\":\"Expiration\",\"Version\":\"1.0\",\"Attributes\":{\"Timestamp\":\"2019-05-13T00:00:00.000Z\"}},{\"Type\":\"ExpirationNotification\",\"Version\":\"1.0\",\"Attributes\":{\"Before\":\"5\",\"Unit\":\"Days\"}},{\"Type\":\"NoChangeNotification\",\"Version\":\"1.0\",\"Attributes\":{\"After\":\"60\",\"Unit\":\"Days\"}}]"
  
Output::

  {
    "Version": 1
  }

**To add a policy to an existing parameter**

This example attaches a policy to an existing advanced parameter.

Command::

  aws ssm put-parameter --name "/Finance/Payroll/elixir3131" --value "N3wP@sSwW)rd" --type "SecureString" --tier Advanced --policies "[{\"Type\":\"Expiration\",\"Version\":\"1.0\",\"Attributes\":{\"Timestamp\":\"2019-05-13T00:00:00.000Z\"}},{\"Type\":\"ExpirationNotification\",\"Version\":\"1.0\",\"Attributes\":{\"Before\":\"5\",\"Unit\":\"Days\"}},{\"Type\":\"NoChangeNotification\",\"Version\":\"1.0\",\"Attributes\":{\"After\":\"60\",\"Unit\":\"Days\"}}]" --overwrite
  
Output::

  {
    "Version": 2
  }
