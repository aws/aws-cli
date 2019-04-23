**To display the default Windows patch baseline**

This example displays the default Windows patch baseline.

Command::

  aws ssm get-default-patch-baseline

Output::

  {
    "BaselineId": "pb-0713accee01612345",
    "OperatingSystem": "WINDOWS"
  }

**To display the default Amazon Linux patch baseline**

This example displays the default Windows patch baseline.

Command::

  aws ssm get-default-patch-baseline --operating-system AMAZON_LINUX

Output::

  {
    "BaselineId": "pb-047c6eb9c8fc12345",
    "OperatingSystem": "AMAZON_LINUX"
  }
