**To deregister a patch group from a patch baseline**

This example deregisters a patch group from a patch baseline.

Command::

  aws ssm deregister-patch-baseline-for-patch-group --patch-group "Production" --baseline-id "arn:aws:ssm:us-west-1:812345678901:patchbaseline/pb-0ca44a362f8afc725"
  
Output::

  {
	"PatchGroup":"Production",
	"BaselineId":"arn:aws:ssm:us-west-1:812345678901:patchbaseline/pb-0ca44a362f8afc725"
  }
