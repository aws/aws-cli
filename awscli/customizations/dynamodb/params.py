# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from awscli.customizations.paginate import (
    MAX_ITEMS_HELP, PAGE_SIZE_HELP, STARTING_TOKEN_HELP
)


TABLE_NAME = {
    'name': 'table_name',
    'positional_arg': True,
    'synopsis': '<table-name>',
    'help_text': '<p>The name of your DynamoDB table.</p>',
}

INDEX_NAME = {
    'name': 'index-name',
    'help_text': (
        '<p>The name of a secondary index to scan. This index can be any '
        'local secondary index or global secondary index.</p>'
    )
}

SELECT = {
    'name': 'attributes',
    'choices': ['ALL', 'ALL_PROJECTED', 'COUNT'],
    'help_text': (
        '<p>The attributes to be returned in the result. You can retrieve all '
        'item attributes, specific item attributes, the count of matching '
        'items, or in the case of an index, some or all of the attributes '
        'projected into the index.</p>'
        '<ul>'
        '<li> ``ALL`` - Returns all of the item attributes from the specified '
        'table or index. If you query a local secondary index, then for each '
        'matching item in the index DynamoDB will fetch the entire item from '
        'the parent table. If the index is configured to project all item '
        'attributes, then all of the data can be obtained from the local '
        'secondary index, and no fetching is required.</li>'
        '<li> ``ALL_PROJECTED`` - Allowed only when querying an index. '
        'Retrieves all attributes that have been projected into the index. '
        'If the index is configured to project all attributes, this return '
        'value is equivalent to specifying ``ALL``.</li>'
        '<li> ``COUNT`` - Returns the number of matching items, rather than '
        'the matching items themselves.</li>'
        '</ul>'
    )
}

PROJECTION_EXPRESSION = {
    'name': 'projection', 'nargs': '+',
    'help_text': (
        '<p>A string that identifies one or more attributes to retrieve from '
        'the specified table or index. These attributes can include scalars, '
        'sets, or elements of a JSON document. The attributes in the '
        'expression must be separated by commas. If any of the requested '
        'attributes are not found, they will not appear in the result.</p>'
        '<p>For more information, see '
        '<a href="https://docs.aws.amazon.com/amazondynamodb/latest/'
        'developerguide/Expressions.ProjectionExpressions.html">'
        'Accessing Item Attributes</a> in the <i>Amazon DynamoDB Developer '
        'Guide</i>.'
        '<p>For CLI specific syntax see '
        '<a href="https://docs.aws.amazon.com/cli/latest/topic/'
        'ddb-expressions.html">aws help ddb-expressions</a></p>'
    )
}

FILTER_EXPRESSION = {
    'name': 'filter', 'nargs': '+',
    'help_text': (
        '<p>A string that contains conditions that DynamoDB applies after the '
        'operation, but before the data is returned to you. Items that do '
        'not satisfy the ``--filter`` criteria are not returned.</p>'
        '<note><p>A ``--filter`` is applied after the items have already been '
        'read; the process of filtering does not consume any additional read '
        'capacity units.</p></note>'
        '<p>For more information, see '
        '<a href="http://docs.aws.amazon.com/amazondynamodb/latest/'
        'developerguide/QueryAndScan.html#FilteringResults">Filter '
        'Expressions</a> in the <i>Amazon DynamoDB Developer Guide</i>.</p>'
        '<p>For CLI specific syntax see '
        '<a href="https://docs.aws.amazon.com/cli/latest/topic/'
        'ddb-expressions.html">aws help ddb-expressions</a></p>'
    )
}

CONDITION_EXPRESSION = {
    'name': 'condition', 'nargs': '+',
    'help_text': (
        '<p>A condition that must be satisfied in order for a conditional '
        '<code>put</code> operation to succeed.</p>'
        '<p>For more information, see '
        '<a href="https://docs.aws.amazon.com/amazondynamodb/latest/'
        'developerguide/Expressions.OperatorsAndFunctions.html">Comparison '
        'Operator and Function Reference</a> in the <i>Amazon DynamoDB '
        'Developer Guide</i></p>'
        '<p>For CLI specific syntax see '
        '<a href="https://docs.aws.amazon.com/cli/latest/topic/'
        'ddb-expressions.html">aws help ddb-expressions</a></p>'
    )
}

KEY_CONDITION_EXPRESSION = {
    'name': 'key-condition', 'nargs': '+',
    'help_text': (
        '<p>The condition that specifies the key value(s) for items to be '
        'retrieved. Must perform an equality test on a single partition key '
        'value.</p> <p>The condition can optionally perform one of several '
        'comparison tests on a single sort key value. This allows '
        '<code>select</code> to retrieve one item with a given partition key '
        'value and sort key value, or several items that have the same '
        'partition key value but different sort key values.</p>'
        '<p>The partition key equality test must be specified in the '
        'following format:</p>'
        '<p><code>partitionKeyName = :partitionkeyval</code></p>'
        '<p>If you also want to provide a condition for the sort key, it must '
        'be combined using <code>AND</code> with the condition for the sort '
        'key.</p>'
        '<p>Valid comparisons for the sort key condition are as follows:</p>'
        '<ul>'
        '<li><p><code>sortKeyName = :sortkeyval</code> - true '
        'if the sort key value is equal to <code>:sortkeyval</code>.</p></li>'
        '<li><p><code>sortKeyName &lt; :sortkeyval</code> - true if the sort '
        'key value is less than <code>:sortkeyval</code>.</p></li>'
        '<li><p><code>sortKeyName &lt;= :sortkeyval</code> - true if the '
        'sort key value is less than or equal to <code>:sortkeyval</code>.'
        '</p></li>'
        '<li><p><code>sortKeyName &gt; :sortkeyval</code> - true if the sort '
        'key value is greater than <code>:sortkeyval</code>.</p></li>'
        '<li><p><code>sortKeyName &gt;= :sortkeyval</code> - true if the '
        'sort key value is greater than or equal to <code>:sortkeyval</code>.'
        '</p></li>'
        '<li><p><code>sortKeyName BETWEEN :sortkeyval1 AND '
        ':sortkeyval2</code> - true if the sort key value is greater than or '
        'equal to <code>:sortkeyval1</code>, and less than or equal to '
        '<code>:sortkeyval2</code>.</p></li>'
        '<li><p><code>begins_with(sortKeyName, :sortkeyval)</code> - true '
        'if the sort key value begins with a particular operand. '
        '(You cannot use this function with a sort key that is of type '
        'Number.) Note that the function name <code>begins_with</code> is '
        'case-sensitive.</p></li>'
        '</ul>'
        '<p>For CLI specific syntax see '
        '<a href="https://docs.aws.amazon.com/cli/latest/topic/'
        'ddb-expressions.html">aws help ddb-expressions</a></p>'
    )
}

ITEMS = {
    'name': 'items',
    'positional_arg': True,
    'synopsis': '<items>',
    'help_text': (
        '<p>One or more items to put into the table, in YAML format.</p>'
    )
}

CONSISTENT_READ = {
    'name': 'consistent-read', 'action': 'store_true', 'default': True,
    'group_name': 'consistent_read', 'dest': 'consistent_read',
    'help_text': (
        '<p>Determines the read consistency model: If set to '
        '<code>--consistent-read</code>, then the operation uses strongly '
        'consistent reads; otherwise, the operation uses eventually '
        'consistent reads. Strongly consistent reads are not supported on '
        'global secondary indexes. If you query a global secondary index '
        'with <code>--consistent-read</code>, you will receive a '
        '<code>ValidationException</code>.</p>'
    )
}

NO_CONSISTENT_READ = {
    'name': 'no-consistent-read', 'action': 'store_false', 'default': True,
    'group_name': 'consistent_read', 'dest': 'consistent_read',
}

RETURN_CONSUMED_CAPACITY = {
    'name': 'return-consumed-capacity', 'action': 'store_true',
    'default': False, 'group_name': 'return_consumed_capacity',
    'dest': 'return_consumed_capacity',
    'help_text': (
        '<p>Will include the aggregate <code>ConsumedCapacity</code> for the '
        'operation. If <code>--index-name</code> is also specified, '
        'then the <code>ConsumedCapacity</code> for each table and secondary '
        'index that was accessed will be returned.</p>'
    )
}

NO_RETURN_CONSUMED_CAPACITY = {
    'name': 'no-return-consumed-capacity', 'action': 'store_false',
    'default': False, 'group_name': 'return_consumed_capacity',
    'dest': 'return_consumed_capacity',
}

MAX_ITEMS = {
    'name': 'max-items',
    'cli_type_name': 'integer',
    'help_text': MAX_ITEMS_HELP,
}

PAGE_SIZE = {
    'name': 'page-size',
    'cli_type_name': 'integer',
    'help_text': PAGE_SIZE_HELP,
}

STARTING_TOKEN = {
    'name': 'starting-token',
    'help_text': STARTING_TOKEN_HELP,
}
