**To retrieve the reservation recommendations for Partial Upfront EC2 RIs with a three year term**

The following ``get-reservation-purchase-recommendation`` example retrieves recommendations for Partial Upfront EC2 instances with a three-year term, based on the last 60 days of EC2 usage. ::

    aws ce get-reservation-purchase-recommendation \
        --service "Amazon Redshift" \
        --lookback-period-in-days SIXTY_DAYS \
        --term-in-years THREE_YEARS \
        --payment-option PARTIAL_UPFRONT

Output::

    {
        "Recommendations": [],
        "Metadata": {
            "GenerationTimestamp": "2018-08-08T15:20:57Z",
            "RecommendationId": "00d59dde-a1ad-473f-8ff2-iexample3330b"
        }
    }

For more information, see `Accessing reservation recommendations <https://docs.aws.amazon.com/cost-management/latest/userguide/ri-recommendations.html>`__ in the *AWS Cost Management User Guide*.
