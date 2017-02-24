**To modify the permissions for a document**

This example adds ``Share`` permissions to ``All`` accounts for document ``RunShellScript``. There is no output if the command succeeds.

Command::

  aws ssm modify-document-permission --name "RunShellScript" --permission-type "Share" --account-ids-to-add "All"
