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

from .RingObject import RingObject

class RingRelationship(RingObject):

    def __init__(self):
        # Set default values
        self.id = None
        self.name = None
        self.fro = None
        self.to = None
        self.join = []
        self.type = "m2m"
        self.bidirectional = True

        self.error_set = set()

        self.rel_list = []
        self.fro_name = None
        self.to_name = None

    def parse(self,
              relationship_config: dict) -> None:
        self.name = relationship_config.get("name")
        self.fro = relationship_config.get("from")
        self.to = relationship_config.get("to")
        self.fro_name = relationship_config.get("fromName")
        self.to_name = relationship_config.get("toName")
        if relationship_config.get("derived"):

            # grab all the other relationships and derived relation and bidirectional
            self.rel_list = relationship_config.get("relationshipList")
            self.join = None # empty for now, ideally would grab all joins from the other relationships

        else:
            self.join = self.safe_extract_list("join", relationship_config)
            self.type = relationship_config.get("relation", "m2m")
            self.bidirectional = relationship_config.get("bidirectional", True)

        # construct an id handle from the inputs
        self.id = "{}{}{}{}".format(self.fro, self.name, self.to, self.join)

    def construct(self):
        rel = {}
        self.safe_insert('id', self.id, rel)
        self.safe_insert('name', self.name, rel)
        self.safe_insert('from', self.fro, rel)
        self.safe_insert('to', self.to, rel)
        self.safe_insert('join', self.join, rel)
        self.safe_insert('relation', self.type, rel)
        self.safe_insert('bidirectional', self.bidirectional, rel)
        return rel

    def is_valid(self):
        if self.name == None:
            self.error_set.add("Ring Relatoinhips 'name' is missing.")
        if self.fro == None:
            self.error_set.add("Ring relationship: 'from' is missing.")
        if self.to == None:
            self.error_set.add("Ring relationship: 'to' is missing.")
        if self.join == []:
            self.error_set.add("Ring relationship has no joins.")

        if len(self.error_set) == 0:
            ## No errors:
            return (True, {})
        else:
            ## will return a string of errors
            errorString = ' '.join(self.error_set)
            return (False, errorString)
