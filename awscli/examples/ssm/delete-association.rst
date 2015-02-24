**To delete an association**

This example deletes the association between instance ``i-bbcc3344`` and the configuration document ``Test_config``. If the command succeeds, no output is returned.

Command::

  aws ssm delete-association --instance-id i-bbcc3344 --name Test_config

