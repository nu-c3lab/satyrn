'''
This file is part of Satyrn.
Satyrn is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.
Satyrn is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Satyrn.
If not, see <https://www.gnu.org/licenses/>.
'''


class SQRField:
    def __init__(self,
                 subplan_name: str,
                 entity_name: str = None,
                 field: str = None,
                 column_name_override: str = None,
                 ontology = None):
        self.subplan_name = subplan_name
        self.entity_name = entity_name
        self.field = field
        self.column_name_override = column_name_override
        self.ontology = ontology

    @property
    def column_name(self):
        if self.column_name_override:
            return self.column_name_override
        elif self.entity_name:
            return f"{self.entity_name}//{self.field}"
        else:
            return f"{self.field.subplan_name}//{self.field.column_name}"

    @property
    def is_analysis_operation(self):
        return type(self.field) == dict and self.ontology.is_analysis_operation(self.field['type'])

    @property
    def is_arithmetic_operation(self):
        return type(self.field) == dict and self.ontology.is_arithmetic_operation(self.field['type'])

    @property
    def satyrn_entity(self):
        if self.is_analysis_operation or self.is_arithmetic_operation:
            return self.field['arguments'][0].satyrn_entity
        elif self.column_name_override:
            return self.entity_name
        else:
            return self.entity_name or self.field.satyrn_entity

    @property
    def satyrn_attribute(self):
        if type(self.field) == dict:
            if self.ontology.is_analysis_operation(self.field['type']) or self.ontology.is_arithmetic_operation(self.field['type']): # and len(self.field['arguments']) == 1:
                return self.field['arguments'][0].satyrn_attribute
            else:
                return None
        if self.entity_name:
            return self.field
        return self.field.satyrn_attribute

    @property
    def has_count_operation(self):
        if type(self.field) == dict:
            if self.field['type'] in ['count', 'count_unique']:
                return True
            else:
                return self.field['arguments'][0].has_count_operation
        elif type(self.field) == SQRField:
            return self.field.has_count_operation
        else:
            return False
