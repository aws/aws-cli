**To create a patch baseline**

This example creates a patch baseline that approves patches for a production environment seven days after they are released by Microsoft.

Command::

  aws ssm create-patch-baseline --name "Production-Baseline" --approval-rules "PatchRules=[{PatchFilterGroup={PatchFilters=[{Key=MSRC_SEVERITY,Values=[Critical,Important,Moderate]},{Key=CLASSIFICATION,Values=[SecurityUpdates,Updates,UpdateRollups,CriticalUpdates]}]},ApproveAfterDays=7}]" --description "Baseline containing all updates approved for production systems"

Output::

  {
    "BaselineId": "pb-045f10b4f382baeda"
  }
