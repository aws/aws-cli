**To download a DB log file**

By default, this command will only download the latest part of your log file::

    aws rds download-db-log-file-portion --db-instance-identifier test-instance \
    --log-file-name log.txt --output text > tail.txt

In order to download the entire file, you need `--starting-token 0` parameter::

    aws rds download-db-log-file-portion --db-instance-identifier test-instance \
    --log-file-name log.txt --starting-token 0 --output text > full.txt

The downloaded file might contain several blank lines.  They appear at the end of each part of the log file while being downloaded.  This will generally not cause any trouble in your log file analysis.
