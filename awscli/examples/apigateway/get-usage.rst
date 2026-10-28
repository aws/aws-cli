**To get the usage details for a Usage Plan**

The following ``get-usage`` example gets the usage details for the specified usage plan between 2016-08-16 and 2016-08-17. ::

    aws apigateway get-usage \
        --usage-plan-id a1b2c3 \
        --start-date "2016-08-16" \
        --end-date "2016-08-17"
