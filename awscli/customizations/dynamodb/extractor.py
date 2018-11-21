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
from .parser import Parser


class AttributeExtractor(object):
    COMPARATORS = {
        'eq': '=',
        'ne': '<>',
        'lt': '<',
        'lte': '<=',
        'gt': '>',
        'gte': '>=',
    }

    def __init__(self, parser=None):
        self._parser = parser
        if parser is None:
            self._parser = Parser()
        self._identifiers = {}
        self._literals = {}
        self._index_offset = 0

    def extract(self, expression, index_offset=0):
        self._identifiers = {}
        self._literals = {}
        self._index_offset = index_offset
        root = self._parser.parse(expression)
        expression = self._visit(root).strip()
        return {
            'expression': expression,
            'identifiers': self._identifiers,
            'values': self._literals,
            'substitution_count': len(self._identifiers) + len(self._literals)
        }

    def _substitution_index(self):
        num_substituted = len(self._identifiers) + len(self._literals)
        return num_substituted + self._index_offset

    def _visit(self, node):
        method = getattr(self, '_visit_%s' % node['type'])
        return method(node)

    def _visit_comparator(self, node):
        left = self._visit(node['children'][0])
        right = self._visit(node['children'][1])
        expression = '%s%s %s' % (
            left, self.COMPARATORS[node['value']], right
        )
        return expression

    def _visit_identifier(self, node):
        identifier_replacement = '#n%s' % self._substitution_index()
        self._identifiers[identifier_replacement] = node['value']
        return '%s ' % identifier_replacement

    def _visit_path_identifier(self, node):
        left = self._visit(node['children'][0]).strip()
        right = self._visit(node['children'][1])
        return '%s.%s' % (left, right)

    def _visit_index_identifier(self, node):
        left = self._visit(node['children'][0]).strip()
        return '%s[%s] ' % (left, node['value'])

    def _visit_literal(self, node):
        literal_replacement = ':n%s' % self._substitution_index()
        self._literals[literal_replacement] = node['value']
        return '%s ' % literal_replacement

    def _visit_sequence(self, node):
        visited_children = []
        for child in node['children']:
            visited_children.append(self._visit(child).strip())
        return '%s' % ', '.join(visited_children)

    def _visit_or_expression(self, node):
        left = self._visit(node['children'][0])
        right = self._visit(node['children'][1])
        return '%sOR %s' % (left, right)

    def _visit_and_expression(self, node):
        left = self._visit(node['children'][0])
        right = self._visit(node['children'][1])
        return '%sAND %s' % (left, right)

    def _visit_not_expression(self, node):
        return 'NOT %s' % self._visit(node['children'][0])

    def _visit_subexpression(self, node):
        return '( %s) ' % self._visit(node['children'][0])

    def _visit_function(self, node):
        return '%s(%s) ' % (node['value'], self._visit_sequence(node).strip())

    def _visit_in_expression(self, node):
        return '%sIN (%s) ' % (
            self._visit(node['children'][0]),
            self._visit(node['children'][1]).strip(),
        )

    def _visit_between_expression(self, node):
        return '%sBETWEEN %sAND %s' % (
            self._visit(node['children'][0]),
            self._visit(node['children'][1]),
            self._visit(node['children'][2]),
        )
