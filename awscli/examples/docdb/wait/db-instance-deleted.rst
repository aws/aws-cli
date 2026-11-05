**To pause running until the specified cluster instance is deleted**

The following ``wait db-instance-deleted`` example pauses and continues only after it can confirm that the specified database cluster instance is deleted. ::

    aws docdb wait db-instance-deleted \
        --db-instance-identifier "sample-instance"

This command produces no output.

For more information, see `Deleting an Amazon DocumentDB instance <https://docs.aws.amazon.com/documentdb/latest/devguide/db-instance-delete.html>`__ in the *Amazon DocumentDB Developer Guide*.
