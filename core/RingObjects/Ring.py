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

import os
import json
from functools import reduce
import networkx as nx
from typing import Union, Tuple, List, Dict, Set

from sqlalchemy.engine.row import Row

from .RingJoin import RingJoin
from .RingObject import RingObject
from .RingEntity import RingEntity
from .RingDataSource import RingDataSource
from .RingRelationship import RingRelationship
from .RingRelationshipGraph import RingRelationshipGraph
from .RingAttribute import RingAttribute

from core.Analysis.OperationOntology import OperationOntology
from core.Operations.ArgType import ArgType

try:
    from core.api.utils import walk_rel_path, mirror_rel, contains_date_denomination
except:
    from ..api.utils import walk_rel_path, mirror_rel, contains_date_denomination

class Ring(RingObject):
    """
    A python object version of the ring file.
    """

    def __init__(self):

        # Initialize properties
        self.name = None
        self.dbid = None
        self.id = None
        self.version = None
        self.schema_version = None
        self.data_source = None
        self.description = None
        self.entities = []
        self.relationships = []
        self.relationship_graph = None
        self.default_target_entity = None

        # Initialize other important properties
        self.db = None
        self.compiler = None

        self.error_set = set()
        self.entity_name = []
        self.rounding = None
        self.sigfigs = None

        # Initialize properties that were previously in the RingInterface class
        self.current_target_entity = None
        self.cache = {}
        self.db_interface = None

    def parse(self,
              configuration: dict) -> None:
        """
        Reads the configuration json and adds it into this object.
        :param configuration: Object containing parameters for the ring.
        :type configuration: dict
        :return: None
        :rtype: None
        """

        self.name = configuration.get('name')
        self.dbid = configuration.get('id')
        self.id = configuration.get('rid')
        self.version = configuration.get('version')
        self.schema_version = configuration.get('schemaVersion', 2)
        if self.schema_version > 2:
            self.default_target_entity = configuration.get('ontology', {}).get('defaultTargetEntity')
        else:
            self.default_target_entity = configuration.get('defaultTargetEntity')
        self.description = configuration.get('description')
        self.parse_source(configuration)
        self.parse_entities(configuration)
        self.parse_relationships(configuration)
        self.parse_config_defaults(configuration)

        # Initialize other properties now that we've parsed the configuration
        self.current_target_entity = self.default_target_entity
        self.cache = {ent.name: {} for ent in self.entities}

        return None

    def parse_config_defaults(self,
                              configuration: dict) -> None:
        # i.e. where to put the attributes in the ring json
        default_path = os.environ.get("SATYRN_ROOT_DIR") + "/" +"core" + "/" + "defaults.json"
        with open(default_path, 'r') as file:
            defaults = json.load(file)
            self.sig_figs = defaults.get("result_formatting")["rounding"][1]
            self.rounding = True

    def parse_source(self,
                     configuration: dict) -> None:
        if 'dataSource' in configuration:
            source = RingDataSource()
            source.parse(configuration['dataSource'])
            self.data_source = source

    def parse_entities(self,
                       configuration: dict) -> None:
        if self.schema_version > 2:
            entities = configuration.get('ontology', {}).get('entities', [])
        else:
            entities = configuration.get('entities', [])
        for entity in entities:
            self.entity_name.append(entity)
            entity_object = RingEntity()
            entity_object.parse(entity)
            self.entities.append(entity_object)

    def parse_relationships(self,
                            configuration: dict) -> None:
        if self.schema_version > 2:
            rels = configuration.get("ontology", {}).get("relationships", [])
        else:
            rels = configuration.get("relationships", [])
        relationship_graph = nx.Graph()
        for rel in rels:
            relationship_object = RingRelationship()
            relationship_object.parse(rel)
            relationship_graph.add_edge(relationship_object.fro, relationship_object.to, relationship=relationship_object.name)
            self.relationships.append(relationship_object)
        self.relationship_graph = RingRelationshipGraph(relationship_graph)


        for idx, rel in enumerate(self.relationships):
            if rel.rel_list:
                # do the derived work
                # get the list of joins?
                rels = {r.name: r for r in self.relationships if r.name in rel.rel_list}

                # self.relationships[idx].join = []
                self.relationships[idx].join = [x for r in rel.rel_list for x in rels[r].join if rels[r].join]

                # get the type of relation (o2o, m2o, m2m, o2m)
                self.relationships[idx].type = walk_rel_path(rel.fro, rel.to, [rels[r] for r in rel.rel_list])

                # get whether it bidirectional or not
                self.relationships[idx].bidirectional = all(rels[r].bidirectional for r in rel.rel_list)

                print(self.relationships[idx])
                print(self.relationships[idx].join)

    def parse_file_from_path(self,
                             path: str) -> None:
        """
        Parses a file given a path.
        :param path: Path to the file
        :type path: str
        :return: None
        :rtype: None
        """
        with open(path, 'r') as file:
            configuration = json.load(file)
            self.parse(configuration)
        return None

    def construct(self):
        configuration = {}
        self.safe_insert('name', self.name, configuration)
        self.safe_insert('version', self.version, configuration)
        self.safe_insert('dataSource', self.data_source.construct(), configuration)
        self.safe_insert('entities', list(map((lambda entity: entity.construct()), self.entities)), configuration)
        return configuration

    def write_to_file_with_path(self,
                                path: str):
        with open(path, 'w') as file:
            configuration = self.construct()
            json.dump(configuration, file, indent=4)

    def is_valid(self) -> Tuple[bool, Union[set, str]]:
        """
        Ensures that the ring configuration is properly constructed.
        :return: Returns true/false along with the error message (if any).
        :rtype: Tuple[bool, set]
        """

        if self.name == None:
            self.error_set.add("Ring configuration 'name' is missing.")
        if self.version == None:
            self.error_set.add("Ring configuration 'version' is missing.")
        if self.data_source == None:
            self.error_set.add("Ring configuration 'Source' is missing.")
        if not self.data_source.is_valid()[0]:
            self.error_set.add("Ring Configuration source is not valid.")
        if self.entities == None:
            self.error_set.add("Ring configuration entities value is not valid.")
        if (True and reduce((lambda x, y: x and y), map((lambda x: x.is_valid()[0]), self.entities))) == False:
            issues = []
            sanityCheck = []
            for i in range(len(self.entities)):
                sanityCheck.append(str(self.entity_name[i]))
                if self.entities[i].is_valid()[0] == False:
                    wholeStr = str(self.entity_name[i])
                    nameSplit = wholeStr.split()[1]
                    issues.append(nameSplit)
                    self.error_set = self.error_set.union(self.entities[i].is_valid()[1])
            self.error_set.add("Ring configuration entity is invalid for " + ' '.join([str(elem) for elem in issues]))
        if len(self.error_set) == 0:
            return (True, set())
        else:
            ## will return a string of errors
            errorString = ' '.join(self.error_set)
            return (False, errorString)

    def get_related_entities(self,
                             entity: RingEntity) -> List[RingEntity]:
        related_entities = []
        for rel in self.relationships:
            if rel.type == "m2o" and entity.name == rel.to:
                related_entities.append([ent for ent in self.entities if ent.name == rel.fro][0])
            elif rel.type == "o2m" and entity.name == rel.fro:
                related_entities.append([ent for ent in self.entities if ent.name == rel.to][0])

        return related_entities

    def get_related_attributes_for_entity(self,
                                          entity: RingEntity,
                                          attr_type: ArgType = None) -> List[RingAttribute]:
        """
        Gets the attributes of entities related to the given entity of the specified attribute type.
        :param entity: The entity to grab the attributes for.
        :type entity: RingEntity
        :param attr_type: The type of the attributes to retrieve.
        :type attr_type: ArgType
        :return: Attributes of related entities with the specified type.
        :rtype: List of RingAttribute
        """
        attrs = []

        related_entities = self.get_related_entities(entity)
        for related_entity in related_entities:
            # Get the attributes of the related entity
            if related_entity:
                if attr_type:
                    attrs.extend([attr for attr_name, attr in related_entity.attributes.items() if attr_type in attr.type])
                else:
                    attrs.extend(list(related_entity.attributes.values()))

        return attrs

    ##############################################################################
    # The following functions were previously in the RingInterface class
    ##############################################################################
    def ensure_entity_exists(self,
                             entity_name: str = None) -> Union[str, None]:
        """
        Ensures the entity with the given name exists.
        :param entity:
        :type entity:
        :return:
        :rtype: The name of the entity
        """
        if entity_name not in self.cache:
            return None
        else:
            return entity_name

    def get_entity_by_name(self,
                           entity_name: str) -> RingEntity:
        """
        Maps the target entity name to the Ring_Entity object. Ensures the target (entity) exists in the ring.
        :param entity_name: The target entity to resolve.
        :type entity_name: str
        :return: The target entity along with its Ring_Entity object.
        :rtype: RingEntity
        """
        # Ensure entity exists before trying to retrieve the associated RingEntity
        entity_name = self.ensure_entity_exists(entity_name)
        return [ent for ent in self.entities if ent.name == entity_name][0]

    def get_join_by_name(self,
                         join_name: str) -> RingJoin:
        """
        Maps the join name to the Ring_Join object in Satyrn.
        :param join_name: The name of the join in the ring.
        :type join_name: str
        :return: The Ring Join object
        :rtype: RingJoin
        """
        return [join for join in self.data_source.joins if join.name == join_name][0]

    def get_relationship_by_name(self,
                                 relationship_name: str) -> RingRelationship:
        """
        Maps the relationship name to the Ring_Relationship object in Satyrn.
        :param relationship_name: The name of the relationship in the ring.
        :type relationship_name: str
        :return: The Ring_Relationship object
        :rtype: RingRelationship
        """
        return [rel for rel in self.relationships if rel.name == relationship_name][0]

    def get_db_type(self):
        return self.data_source.type

    def get_rounding(self):
        return self.rounding

    def get_sig_figs(self):
        return self.sig_figs

    def get_all_attributes(self,
                           type: str = None):
        for entity in self.entities:
            # for attribute in filter(lambda attr: not type or type in map(lambda t: t.name, attr.type), entity.attributes.values()):
            for attribute in entity.get_attributes_with_type(type):
                yield attribute

    def get_entity_relationships(self,
                                 init_ent: str) -> List[RingRelationship]:
        """
        Retrieves all relationships from the initial entity to other entities in the ring (including the relationship with itself).
        :param init_ent: The entity whose 1st degree relationships are retrieved.
        :type init_ent: str
        :return: A list of relationships between the initial_ent and other entities.
        :rtype: List[RingRelationship]
        """

        entity_relationships = []

        # Add unnamed relationship with itself
        default_rel = RingRelationship()
        default_rel.fro = init_ent
        default_rel.to = init_ent
        default_rel.name = None
        default_rel.type = "o2o"
        entity_relationships.append(default_rel)

        # Get the relationships the initial entity has with other relationships (ensures no duplicated rels are added)
        ent_rels = [rel for rel in self.get_connected_entity_relationships(init_ent) if rel not in entity_relationships]
        entity_relationships.extend(ent_rels)

        return entity_relationships

    def get_connected_entity_relationships(self,
                                           target: str = None) -> List[RingRelationship]:
        """
        Retrieves the first degree relationships from the initial entity to other entities in the ring.
        :param target: The target entity.
        :type target: str
        :return: List of the relationships this target entity has with other entities.
        :rtype: List[RingRelationship]
        """
        if not target:
            target = self.current_target_entity
        relationships = []

        for rel in self.relationships:  # relationship in the config (given in the json) is added here in entities
            if target in [rel.fro, rel.to]:
                relationships.append(rel)
        return relationships

    def get_primary_key(self,
                        table):
        for each in self.data_source.tables:
            eachlist = list(each.values())
            if table in eachlist:
                return eachlist[1]
        # add error message if the name is not found in the table

    def get_joins_between_entities(self,
                                        entity_a: str,
                                        entity_b: str) -> set:
        return {join for rel_name in self.relationship_graph.get_path(entity_a, entity_b) for join in self.get_relationship_by_name(rel_name).join}

    # To find the backref of a given relationship in the table
    # rel_name: name f the relationship
    # table_name: name of the tabe, the rel_name exists
    # returns a dictionary with the backref and the primary join path

    def get_related_relationship(self,
                                 rel_name,
                                 table_name):
        entity = getattr(self.db, table_name)
        rel = getattr(entity, rel_name)
        return {'join': rel.property.primaryjoin, 'back_ref': rel.property.back_populates}

    def coerce_vals_to_string(self,
                              vals: list,
                              formatting: List[bool]) -> str:
        """
        Converts the values to strings in the format specified by the user.
        :param vals: The value to format
        :type vals: any
        :param formatting: The formatting parameters
        :type formatting: A list of booleans
        :return: The formatted string
        :rtype: str
        """

        if formatting[0] and formatting[1]:
            return ("{}, {}".format(*vals))
        else:
            tmpl = ("{} " * len(vals)).strip()
            return tmpl.format(*vals)

    def generate_info(self,
                      target=None) -> dict:
        target = self.ensure_entity_exists(target)
        if "feInfo" in self.cache[target]:
            return self.cache[target]["feInfo"]
        output = {
            "targetEntities": [ent.name for ent in self.entities],
            "defaultEntity": self.current_target_entity,
            "targetModelName": target
        }
        self.cache[target]["feInfo"] = output
        return output

    def get_attribute_joins(self,
                            entity_name: str,
                            attribute_name: str) -> Set[str]:
        """
        Get the joins needed to query on this attribute.
        :param entity_name:
        :type entity_name:
        :param attribute_name:
        :type attribute_name:
        :return: A list of the joins required for use this attribute.
        :rtype: list of str
        """
        joins_todo = set()
        # Get the entity object corresponding to the given entity name
        entity_obj = self.get_entity_by_name(entity_name)

        if attribute_name != 'id':
            date_denomination = contains_date_denomination(attribute_name)
            #get the attribute object from the entity
            if date_denomination:
                attr_obj = entity_obj.attributes[date_denomination.group(1)]
            else:
                attr_obj = entity_obj.attributes[attribute_name]
            #check if attr_obj need a join or not
            if attr_obj.source_table != entity_obj.primary_table:
                # Get the joins for multi-table entities (multi-table entity)
                for item in attr_obj.source_joins:
                    joins_todo.add(item)
        return joins_todo

    def get_table_name(self,
                       entity_name: str,
                       attribute_name: str) -> str:
        """
        Returns the table name corresponding to an entity's attribute in the ring.
        :param ring_interface:
        :type ring_interface:
        :param entity_name:
        :type entity_name:
        :param attribute_name: 
        :type attribute_name:
        :return:
        :rtype:
        """

        #get the entity obj
        entity_obj = self.get_entity_by_name(entity_name)


        if attribute_name not in ['id','reference']:
            #get the attribute obj
            attr_obj = entity_obj.attributes[attribute_name]

            #fetch the source_table name from the attr_obj
            model_name = attr_obj.source_table
        
        else:
            model_name = entity_obj.primary_table

        return model_name

    def check_relationship_exists(self,
                                  fro: str,
                                  to: str,
                                  type: str) -> bool:
        ret =  any([relationship.fro == fro and relationship.to == to and relationship.type == type for relationship in self.relationships]) or \
               any([relationship.to == fro and relationship.fro == to and relationship.type == type[::-1] for relationship in self.relationships])
        return ret
