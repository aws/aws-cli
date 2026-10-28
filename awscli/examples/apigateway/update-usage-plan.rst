**Example 1: To change the period defined in a Usage Plan**

The following ``update-usage-plan`` example changes the period defined in a Usage Plan. ::

    aws apigateway update-usage-plan \
        --usage-plan-id a1b2c3 \
        --patch-operations op="replace",path="/quota/period",value="MONTH"

**Example 2: To change the quota limit defined in a Usage Plan**

The following ``update-usage-plan`` example changes the quota limit defined in a Usage Plan. ::

    aws apigateway update-usage-plan \
        --usage-plan-id a1b2c3 \
        --patch-operations op="replace",path="/quota/limit",value="500"

**Example 3: To change the throttle rate limit defined in a Usage Plan**

The following ``update-usage-plan`` example changes the throttle rate limit defined in a Usage Plan. ::

    aws apigateway update-usage-plan \
        --usage-plan-id a1b2c3 \
        --patch-operations op="replace",path="/throttle/rateLimit",value="10"

**Example 4: To change the throttle burst limit defined in a Usage Plan**

The following ``update-usage-plan`` example changes the throttle burst limit defined in a Usage Plan. ::

    aws apigateway update-usage-plan \
        --usage-plan-id a1b2c3 \
        --patch-operations op="replace",path="/throttle/burstLimit",value="20"
