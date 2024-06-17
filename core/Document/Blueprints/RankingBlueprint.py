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

import json
from pathlib import Path
from typing import Dict, List, Tuple

from core.RingObjects.Ring import Ring
from core.Document.Blueprints.utils import build_metric_name

class RankingBlueprint():
    """
    Produces a set of information requirements for a single entity instance.
    """
    def __init__(self,
                 entity_name: str,
                 entity_instance_identifier_attribute_name: str,
                 entity_instance_identifier_value: str,
                 entity_reference: str,
                 metric_entity_name: str,
                 metric_attribute_name: str,
                 metric_aggregation: str,
                 metric_set_filter: Dict[str, str],
                 metric_sort_direction: str,
                 metric_preference_direction: str,
                 ring: Ring):
        super().__init__()
        self.entity_name = entity_name
        self.entity_instance_identifier_attribute_name = entity_instance_identifier_attribute_name
        self.entity_instance_identifier_value = entity_instance_identifier_value
        self.entity_reference = entity_reference
        self.metric_entity_name = metric_entity_name
        self.metric_attribute_name = metric_attribute_name
        self.metric_aggregation = metric_aggregation
        self.metric_sort_direction = metric_sort_direction
        self.metric_preference_direction = metric_preference_direction

        self.metric_set_filter = metric_set_filter

        self.limit = 3

        self.ring = ring
        self.entity_group = self.ring.get_entity_by_name(self.entity_name).nicename[1]

        # Read in the JSON file of info_requirements.json
        p = Path(__file__).with_name('base_plan_templates.json')
        with p.open('r') as f:
            self.base_plan_templates = json.load(f)

        # Generate / retrieve some useful information about the entity and metric
        self.metric_name = build_metric_name(self.metric_aggregation, self.metric_entity_name, self.metric_attribute_name)
        self.entity_access_plan = self.get_entity_access_plan()
        self.metric_access_plan, self.metric_nicename = self.get_metric_access_plan_and_nicename(self.metric_name)
        self.instance_filter = self.get_instance_filter()

        self.requirements = {}

    def get_plan_composition_specs(self) -> List[Dict]:
        """

        :return: A list of dictionaries, each of which contains keys for "base_plan", "access_plan", "access_plan_filters", and "slot_fillers".
        :rtype: List of dictionaries
        """

        composition_specs = []

        # Get the metric value for the entity instance
        composition_specs.append(self.get_metric_value_for_entity_instance())

        # Get the total number of entities being ranked
        composition_specs.append(self.get_num_items_to_rank_plan())

        # Get the rank for the target entity instance according to the specified metric
        composition_specs.append(self.get_rank_of_entity_instance_plan())

        # Get the top three entity instances in the ranking according to the specified metric
        composition_specs.append(self.get_top_three_instances())

        # Compute how far away from the top of the ranking the target entity instance is according to the specified metric
        composition_specs.append(self.get_distance_from_max())

        # Compute the average value of the specified metric for all entities being ranked
        composition_specs.append(self.get_aggregated_value_of_metric('average'))

        # Compute min and max of the metric for all entities
        composition_specs.append(self.get_aggregated_value_of_metric('min'))
        composition_specs.append(self.get_aggregated_value_of_metric('max'))

        # Figure out if the target entity instance's comparative metric value is greater than the average for all entities of the same type
        composition_specs.append(self.get_is_instance_metric_greater_than_average_for_all())

        return composition_specs

    def get_entity_access_plan(self) -> Dict:
        # Get the ring entity
        ring_entity = [ent for ent in self.ring.entities if ent.name == self.entity_name][0]

        # Get the attribute from the ring
        ring_attribute = ring_entity.attributes[self.metric_name]

        # Return the access plan for that attribute
        return ring_attribute.access_plan

    def get_metric_access_plan_and_nicename(self,
                                            metric_name: str) -> Tuple[Dict, str]:
        # Get the ring entity
        ring_entity = [ent for ent in self.ring.entities if ent.name == self.entity_name][0]

        # Get the attribute from the ring
        ring_attribute = ring_entity.attributes[metric_name]

        # Get the nicename for the metric
        metric_nicename = ring_attribute.nicename[0]

        # Return the access plan for that attribute
        return ring_attribute.access_plan, metric_nicename

    def get_instance_filter(self) -> Dict:
        return {
            "|1|": f"(retrieve_entity {self.entity_name})",
            "|2|": f"(retrieve_attribute |1| {self.entity_instance_identifier_attribute_name})",
            "|3|": f"(exact |2| \"{self.entity_instance_identifier_value}\")",
        }

    def get_metric_value_for_entity_instance(self) -> Dict:
        """

        :return:
        :rtype:
        """
        return {
            "plan_name": "InstanceMetricValue",
            "base_plan": self.base_plan_templates["InstanceMetricValue"],
            "access_plans": {
                "|A|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.metric_set_filter],
                        "filter_joiner": None
                    } if self.metric_set_filter else {"filters": [], "filter_joiner": None}
                }
            },
            "slot_fillers": {
                "String:0": self.entity_instance_identifier_value,
                "EntityReference:0": self.entity_reference,
                "Filter:0": ""
            }
        }

    def get_num_items_to_rank_plan(self) -> Dict:
        """

        :return: The composition specifications.
        :rtype: Dict
        """
        return {
            "plan_name": "EntityCount",
            "base_plan": self.base_plan_templates["EntityCount"],
            "access_plans": {
                "|A|": {
                    "access_plan": self.entity_access_plan,
                    "access_plan_filters": {
                        "filters": [self.metric_set_filter],
                        "filter_joiner": None
                    } if self.metric_set_filter else {"filters": [], "filter_joiner": None},
                }
            },
            "slot_fillers": { }
        }

    def get_rank_of_entity_instance_plan(self) -> Dict:
        """

        :return:
        :rtype:
        """
        return {
            "plan_name":"InstanceRank",
            "base_plan": self.base_plan_templates["InstanceRank"],
            "access_plans": {
                "|A|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.metric_set_filter],
                        "filter_joiner": None
                    } if self.metric_set_filter else {"filters": [], "filter_joiner": None}
                }
            },
            "slot_fillers": {
                "String:0": self.entity_instance_identifier_value,
                "EntityReference:0": self.entity_reference,
                "Direction:0": self.metric_sort_direction
            }
        }

    def get_top_three_instances(self) -> Dict:
        """

        :return:
        :rtype:
        """
        plan = "TopThreeForMetric" if self.metric_sort_direction == 'desc' else "BottomThreeForMetric"
        return {
            "plan_name": plan,
            "base_plan": self.base_plan_templates[plan],
            "access_plans": {
                "|A|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.metric_set_filter],
                        "filter_joiner": None
                    } if self.metric_set_filter else {"filters": [], "filter_joiner": None}
                }
            },
            "slot_fillers": {
                "Quantity:0": self.limit
            }
        }

    def get_distance_from_max(self) -> Dict:
        """

        :return:
        :rtype:
        """
        plan = "InstanceDistanceFromMax" if self.metric_sort_direction == 'desc' else "InstanceDistanceFromMin"
        return {
            "plan_name": plan,
            "base_plan": self.base_plan_templates[plan],
            "access_plans": {
                "|A|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.metric_set_filter],
                        "filter_joiner": None
                    } if self.metric_set_filter else {"filters": [], "filter_joiner": None}
                },
                "|B|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.metric_set_filter],
                        "filter_joiner": None
                    } if self.metric_set_filter else {"filters": [], "filter_joiner": None}
                }
            },
            "slot_fillers": {
                "String:0": self.entity_instance_identifier_value,
                "EntityReference:0": self.entity_reference,
                "String:1": self.entity_group
            }
        }

    def get_aggregated_value_of_metric(self,
                                       aggregation: str) -> Dict:
        """

        :return:
        :rtype:
        """
        return {
            "plan_name": "AggregateMetric",
            "base_plan": self.base_plan_templates["AggregateMetric"],
            "access_plans": {
                "|A|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.metric_set_filter],
                        "filter_joiner": None
                    }
                }
            },
            "slot_fillers": {
                "Analysis:0": aggregation,
                "Filter:0": ""
            }
        }

    def get_is_instance_metric_greater_than_average_for_all(self) -> Dict:
        """

        :return:
        :rtype:
        """
        plan = "InstanceGreaterThanAggregatedMetric" if self.get_target_range() == '+inf' else "InstanceLessThanAggregatedMetric"
        return {
            "plan_name": plan,
            "base_plan": self.base_plan_templates[plan],
            "access_plans": {
                "|A|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.metric_set_filter],
                        "filter_joiner": None
                    }
                },
                "|B|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.metric_set_filter],
                        "filter_joiner": None
                    } if self.metric_set_filter else {"filters": [], "filter_joiner": None}
                }
            },
            "slot_fillers": {
                "Analysis:0": "average",
                "String:0": self.entity_instance_identifier_value,
                "EntityReference:0": self.entity_reference
            }
        }

    @staticmethod
    def parse(utterance, feature_extractor):
        return feature_extractor.extract_entity_instance(utterance)

    def get_target_range(self):
        return self.metric_preference_direction or self.ring.get_entity_by_name(self.metric_entity_name).metrics[self.metric_attribute_name][0]

    def build_baseline_prompt(self,
                              entity_reference: str,
                              filter_statement: str) -> str:
        return f"Generate a report for {entity_reference} ranking it according to {self.metric_nicename}{' ' + filter_statement if filter_statement else ''}. " \
        f"{'Higher' if self.metric_preference_direction == '+inf' else 'Lower'} values are considered better."

    def build_prompting_instructions(self) -> str:
        return f"The audience is educated, but may not understand technical terms. " \
               f"Please use natural sounding language and try to find more natural terms for the groups that are mentioned."

    def build_baseline_prompt_with_facts(self,
                                         entity_reference: str,
                                         filter_statement: str,
                                         factual_statements: List[str]) -> str:
        prompt = "Context:\n{}".format('\n'.join(factual_statements))
        prompt += "\n\n" + self.build_baseline_prompt(entity_reference, filter_statement)
        prompt += " Use only the facts provided in the context. "
        prompt += self.build_prompting_instructions()
        return prompt

    def build_baseline_prompt_with_info_reqs(self,
                                             entity_reference: str,
                                             filter_statement: str) -> str:
        prompt = self.build_baseline_prompt(entity_reference, filter_statement)
        prompt += f" The metric is {self.metric_nicename}. " \
                  f"In the report, include information about the value of the metric for {entity_reference}, " \
                  f"the total number of entities being ranked, " \
                  f"the rank of {entity_reference} according to the metric, " \
                  f"the top three {self.entity_name} according to the metric, " \
                  f"how far away from the top of the ranking {entity_reference} is according to the metric, " \
                  f"the average value of the metric for all {self.entity_name}, " \
                  f"the minimum value of the metric for all {self.entity_name}, "\
                  f"the maximum value of the metric for all {self.entity_name}, " \
                  f"and whether or not the metric value for {entity_reference} is greater than the average value of the metric for all {self.entity_name}."
        prompt += "\n\n" + self.build_prompting_instructions()
        return prompt
