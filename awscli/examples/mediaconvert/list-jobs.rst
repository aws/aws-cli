**To get details for all jobs in a region**

The following example requests the information for all of your jobs in the specified region:

Command::
     aws --endpoint-url=https://abcd1234.mediaconvert.region-name-1.amazonaws.com --region=region-name-1 mediaconvert list-jobs

*Optional Parameters*  
  
--max-results <value>
     Limits the number of jobs returned to the <value> that you specify.

--order <value>
     Specifies the order that values are returned in. <value> can be ASCENDING or DESCENDING.

--queue <value>
     Limits the jobs returned to only jobs that are assigned to the queue that you specify. <value> must be the name of one of your queues. This value is case-sensitive.

--status <value>    
     Limits the jobs returned to those with the status that you specify. <value> can be one of the following: CANCELED, SUBMITTED, PROGRESSING, ERROR, or COMPLETE.
