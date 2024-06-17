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

from typing import List

from .RingObject import RingObject
from .RingAttribute import RingAttribute

from core.Operations.ArgType import ArgType

class RingEntity(RingObject):

    def __init__(self):

        # Set default values
        self.id = ['id']
        self.id_type = ['integer']

        # Initialize other properties
        self.name = None
        self.nicename = None
        self.primary_table = None
        self.reference = None
        self.attributes = {}
        self.metrics = {}

        ## Error handling
        self.error_set = set()
        self.attribute_name = []

    def parse(self,
              entity_config: dict) -> None:
        self.name = entity_config.get('name')
        self.nicename = entity_config.get('nicename', [entity_config.get('name'), entity_config.get('name')])
        self.reference = entity_config.get('reference')
        self.primary_table = entity_config.get('table')
        self.id = self.safe_extract_list('id', entity_config)
        self.id_type = self.safe_extract_list('idType', entity_config)
        self.parse_attributes(entity_config)
        self.parse_metrics(entity_config)

    def parse_metrics(self,
                      entity_config: dict) -> None:
        if 'metrics' in entity_config:
            self.metrics = entity_config['metrics']

    def parse_attributes(self,
                         entity_config: dict) -> None:
        if 'attributes' in entity_config:
            attributes = entity_config['attributes']
            for name, info in attributes.items():
                attribute = RingAttribute(entity_config)
                attribute.parse(name, info)
                self.attribute_name.append(name)
                self.attributes[name] = attribute

    def construct(self):
        entity = {}
        self.safe_insert('id', self.id, entity)
        self.safe_insert('idType', self.id_type, entity)
        self.safe_insert('name', self.name, entity)
        self.safe_insert('table', self.primary_table, entity)
        self.safe_insert('attributes', self.attributes, entity)
        return entity

    def is_valid(self):
        if self.name == None:
            self.error_set.add("Ring Entity 'name' is missing.")
        if self.primary_table == None:
            self.error_set.add("Ring Entity 'Table' is missing.")
        if self.id == None:
            self.error_set.add("Ring Attribute 'id' is missing.")
        if self.id_type == None:
            self.error_set.add("Ring Attribute 'id type' is missing.")
        if self.attributes == None:
            self.error_set.add("Ring Attributes are invalid.")
        ## now check to make sure the individual attributes are valid
        for att, att_obj in self.attributes.items():
            if not att_obj.is_valid()[0]:
                self.error_set.add("Ring Attribute is invalid.")

        if len(self.error_set) == 0:
            return (True, {})
        else:
            ## will return a string of errors
            errorString = ' '.join(self.error_set)
            return (False, self.error_set)

    def get_attributes_with_type(self,
                                 attr_type: ArgType) -> List[RingAttribute]:
        """
        Gets all attributes of this entity that have the given ArgType.
        Note: Does not attributes on related entities.
        :param attr_type: The ArgType which the attribute should have.
        :type attr_type: ArgType
        :return: The attributes with the specified type.
        :rtype: List of RingAttribute
        """
        return [attr for attr_name, attr in self.attributes.items() if attr_type in attr.type]
