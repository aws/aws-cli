**To revoke the permission of another Amazon Web Services account to be able to put events to the specified event bus**

The following ``remove-permission`` revokes the permission of another Amazon Web Services account to be able to put events to the specified event bus. Specify the account to revoke by the StatementId value that you associated with the account when you granted it permission with PutPermission. If the command succeeds, no output is returned. ::

	aws events remove-permission \
		--statement-id allow_account_to_manage_rules_they_created \
		--event-bus-name CustomBus

For more information, see `Managing event bus permissions in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-bus-permissions-manage.html>`__ in the *Amazon EventBridge User Guide*.