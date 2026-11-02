**To pause running until the specified instance is available**

The following ``wait db-instance-available`` example pauses and continues only after it can confirm that the specified database cluster instance is available. ::

    aws docdb wait db-instance-available \
        --db-instance-identifier "sample-instance"

This command produces no output.

For more information, see `Describing Amazon DocumentDB instances <https://docs.aws.amazon.com/documentdb/latest/devguide/db-instance-view-details.html>`__ in the *Amazon DocumentDB Developer Guide*.
