**To delete an association**

This example deletes the association between an instance and a document. There is no output if the command succeeds.

Command::

  aws ssm delete-association --instance-id "i-1234567890abcdef0" --name "AWS-UpdateSSMAgent"

**To delete an association using the association ID**

This example deletes the association for the specified association ID. There is no output if the command succeeds.

Command::

  aws ssm delete-association --association-id "8dfe3659-4309-493a-8755-0123456789ab"
