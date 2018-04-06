**To get your account-specific endpoint**

The following example gets the endpoint that you need to send any other request to the service:

Command::
     aws mediaconvert describe-endpoints
	 
Output::	 
{
    "Endpoints": [
        {
            "Url": "https://abcd1234.mediaconvert.region-name-1.amazonaws.com"
        }
    ]
}
