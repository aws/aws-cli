**To deregister a patch group from a patch baseline**

This example deregisters patch group ``Production`` from patch baseline ``arn:aws:ssm:us-west-1:<aws_account_id>:patchbaseline/pb-0ca44a362f8afc725``.

Command::

  aws ssm deregister-patch-baseline-for-patch-group --patch-group "Production" --baseline-id "arn:aws:ssm:us-west-1:<aws_account_id>:patchbaseline/pb-0ca44a362f8afc725"
  
Output::

  {
	"PatchGroup":"Production",
	"BaselineId":"arn:aws:ssm:us-west-1:<aws_account_id>:patchbaseline/pb-0ca44a362f8afc725"
  }
