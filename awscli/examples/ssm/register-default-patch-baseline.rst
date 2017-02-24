**To set the default patch baseline**

This example registers patch baseline ``pb-08b654cf9b9681f04`` as the default patch baseline for region ``us-west-2``.

Command::

  aws ssm register-default-patch-baseline --region "us-west-2" --baseline-id "pb-08b654cf9b9681f04"

Output::

  {
	"BaselineId":"pb-08b654cf9b9681f04"
  }
