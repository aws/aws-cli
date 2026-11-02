**To deregister a DB proxy target from database target group**

The following ``deregister-db-proxy-targets`` example removes the association between the proxy ``proxyExample`` and its target. ::

    aws rds deregister-db-proxy-targets \
        --db-proxy-name proxyExample \
        --db-instance-identifiers database-1

This command produces no output.

For more information, see `Deleting an RDS Proxy <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy-deleting.html>`__ in the *Amazon RDS User Guide* and `Deleting an RDS Proxy <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-proxy-deleting.html>`__ in the *Amazon Aurora User Guide*.