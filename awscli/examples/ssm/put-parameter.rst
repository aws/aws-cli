**To create a parameter that uses a String data type**

This example creates a parameter. There is no output if the command succeeds.

Command::

  aws ssm put-parameter --name "welcome" --type "String" --value "helloWorld"

**To create a Secure String parameter**

This example creates a Secure String parameter. Singles quotes are used so that the literal value is passed. There is no output if the command succeeds.

Command::

  aws ssm put-parameter --name 'password' --type "SecureString" --value 'a value, for example P@ssW%rd#1'

**To change a parameter value**

This example changes the value of a parameter. There is no output if the command succeeds.

Command::

  aws ssm put-parameter --name "welcome" --type "String" --value "good day sunshine" --overwrite
  
