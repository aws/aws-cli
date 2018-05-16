**To get the limit on health checks, hosted zones, reusable delegation sets, traffic policies, and traffic policy instances**

Use the following commands to get the current limit on various Route 53 objects that you can create using the current AWS account.

**Health checks**

  aws route53 get-account-limit --type MAX_HEALTH_CHECKS_BY_OWNER

**Hosted zones**

  aws route53 get-account-limit --type MAX_HOSTED_ZONES_BY_OWNER

**Reusable delegation sets**

  aws route53 get-account-limit --type MAX_REUSABLE_DELEGATION_SETS_BY_OWNER

**Traffic policies**

  aws route53 get-account-limit --type MAX_TRAFFIC_POLICIES_BY_OWNER

**Traffic policy instances**

  aws route53 get-account-limit --type MAX_TRAFFIC_POLICY_INSTANCES_BY_OWNER