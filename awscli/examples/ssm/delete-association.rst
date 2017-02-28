**To delete an association**

This example deletes the association between instance ``i-0cb2b964d3e14fd9f`` and the configuration document ``AWS-UpdateSSMAgent``. There is no output if the command succeeds.

Command::

  aws ssm delete-association --instance-id "i-0cb2b964d3e14fd9f" --name "AWS-UpdateSSMAgent"
