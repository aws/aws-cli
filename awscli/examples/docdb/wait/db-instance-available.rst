**To pause running until the specified instance is available**

The following ``wait db-instance-available`` example pauses and continues only after it can confirm that the specified database cluster instance is available. ::

    aws docdb wait db-instance-available \
        --db-instance-identifier "sample-instance"

This command produces no output.
