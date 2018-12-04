"""Placeholder module for fleshing out the server side model interface.

"""
import json


class DBCompletionLookup(object):
    _QUERY = """\
        SELECT apicall_data from apicall_table
        INNER JOIN param_table
        ON apicall_table.param_id = param_table.param_id
        WHERE
          argname = :argname AND
          command = :command AND
          parent = :parent
    """

    def __init__(self, db_connection):
        self._db_connection = db_connection

    def get_server_completion_data(self, lineage, command_name, param_name):
        parent = '.'.join(lineage)
        results = self._db_connection.execute(
            self._QUERY, argname=param_name,
            command=command_name, parent=parent)
        match = results.fetchone()
        if match is not None:
            return json.loads(match[0])
