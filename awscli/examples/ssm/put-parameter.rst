**To create a parameter that uses a String data type**

This example creates a parameter. There is no output if the command succeeds.

Command::

  aws ssm put-parameter --name "welcome" --type "String" --value "helloWorld"

**To change a parameter value**

This example changes the value of a parameter. There is no output if the command succeeds.

Command::

  aws ssm put-parameter --name "welcome" --type "String" --value "good day sunshine" --overwrite
  