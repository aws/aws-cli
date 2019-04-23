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
  
Output::

  {
    "Version": 1
  }
  
**To change a parameter value**

This example changes the value of a parameter.

Command::

  aws ssm put-parameter --name "welcome" --type "String" --value "good day sunshine" --overwrite
  
Output::

  {
    "Version": 2
  }
