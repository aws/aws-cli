**To set the default patch baseline**

This example registers patch baseline ``pb-08b654cf9b9681f04`` as the default patch baseline.

Command::

  aws ssm register-default-patch-baseline --baseline-id "pb-08b654cf9b9681f04"

Output::

  {
	"BaselineId":"pb-08b654cf9b9681f04"
  }
