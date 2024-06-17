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

class TimeOverTimeBlueprint():
    def __init__(self,
                 entity_name: str,
                 entity_instance_identifier_attribute_name: str,
                 entity_instance_identifier_value: str,
                 entity_reference: str,
                 metric_entity_name: str,
                 metric_attribute_name: str,
                 metric_aggregation: str,
                 metric_set_filter: Dict[str, str],
                 metric_preference_direction: str,
                 time_attribute_name: str,
                 time_zero: str,
                 time_one: str,
                 ring: Ring):
        super().__init__()
        self.entity_name = entity_name
        self.entity_instance_identifier_attribute_name = entity_instance_identifier_attribute_name
        self.entity_instance_identifier_value = entity_instance_identifier_value
        self.entity_reference = entity_reference
        self.metric_entity_name = metric_entity_name
        self.metric_attribute_name = metric_attribute_name
        self.metric_aggregation = metric_aggregation
        self.metric_preference_direction = metric_preference_direction

        self.metric_set_filter = metric_set_filter

        self.time_attribute_name = time_attribute_name
        self.time_zero = time_zero
        self.time_one = time_one

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
        self.time_zero_filter = self.get_time_filter(self.time_zero)
        self.time_one_filter = self.get_time_filter(self.time_one)

        self.requirements = {}

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

    def get_instance_filter(self) -> Dict[str, str]:
        return {
            "|1|": f"(retrieve_entity {self.entity_name})",
            "|2|": f"(retrieve_attribute |1| {self.entity_instance_identifier_attribute_name})",
            "|3|": f"(exact |2| \"{self.entity_instance_identifier_value}\")",
        }

    def get_time_filter(self,
                        time_value: str) -> Dict[str, str]:
        return {
            "|1|": f"(retrieve_entity {self.metric_entity_name})",
            "|2|": f"(retrieve_attribute |1| {self.time_attribute_name})",
            "|3|": f"(exact |2| \"{time_value}\")",
        }

    def get_plan_composition_specs(self) -> List[Dict]:
        """

        :return: A list of dictionaries, each of which contains keys for "base_plan", "access_plan", "access_plan_filters", and "slot_fillers".
        :rtype: List of dictionaries
        """
        composition_specs = []

        # Get the metric value at time t0 for the target entity
        composition_specs.append(self.get_instance_metric_value_at_time(self.time_zero_filter, self.time_zero))

        # Get the metric value at time t1 for the target entity
        composition_specs.append(self.get_instance_metric_value_at_time(self.time_one_filter, self.time_one))

        # Get the percent change between t1 and t0 for the target entity
        composition_specs.append(self.get_instance_percent_change_over_time())

        # Get the average metric value at time t0 for all entities
        composition_specs.append(self.get_aggregated_metric_value_at_time('average', self.time_zero_filter, self.time_zero))

        # Get the min and max of the aggregated attribute at time t0 for all entities
        composition_specs.append(self.get_aggregated_metric_value_at_time('min', self.time_zero_filter, self.time_zero))
        composition_specs.append(self.get_aggregated_metric_value_at_time('max', self.time_zero_filter, self.time_zero))

        # Get the average metric value at time t1 for all entities
        composition_specs.append(self.get_aggregated_metric_value_at_time('average', self.time_one_filter, self.time_one))

        # Get the min and max of the aggregated attribute at time t1 for all entities
        composition_specs.append(self.get_aggregated_metric_value_at_time('min', self.time_one_filter, self.time_one))
        composition_specs.append(self.get_aggregated_metric_value_at_time('max', self.time_one_filter, self.time_one))

        # Get the percent change between t1 and 0 for all entities
        composition_specs.append(self.get_average_percent_change_over_time())

        # Check if the percent change for target entity is greater than the percent change for all entities
        composition_specs.append(self.get_is_instance_cot_greater_than_average_cot())

        return composition_specs

    def get_instance_metric_value_at_time(self,
                                          time_filter: Dict[str, str],
                                          time_value: str) -> Dict:
        return {
            "plan_name": "InstanceMetricValue",
            "base_plan": self.base_plan_templates["InstanceMetricValue"],
            "access_plans": {
                "|A|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [time_filter, self.instance_filter, self.metric_set_filter if self.metric_set_filter else None],
                        "filter_joiner": "and"
                    }
                }
            },
            "slot_fillers": {
                "String:0": self.entity_instance_identifier_value,
                "EntityReference:0": self.entity_reference,
                "Filter:0": "for " + str(time_value)
            }
        }

    def get_aggregated_metric_value_at_time(self,
                                            aggregation: str,
                                            time_filter: Dict[str, str],
                                            time_value: str) -> Dict:
        return {
            "plan_name": "AggregateMetric",
            "base_plan": self.base_plan_templates["AggregateMetric"],
            "access_plans": {
                "|A|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [time_filter, self.metric_set_filter if self.metric_set_filter else None],
                        "filter_joiner": "and"
                    }
                }
            },
            "slot_fillers": {
                "Analysis:0": aggregation,
                "Filter:0": "for " + str(time_value)
            }
        }

    def get_instance_percent_change_over_time(self) -> Dict:
        return {
            "plan_name": "InstancePercentChangeOverTime",
            "base_plan": self.base_plan_templates["InstancePercentChangeOverTime"],
            "access_plans": {
                "|A|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.time_zero_filter, self.instance_filter, self.metric_set_filter if self.metric_set_filter else None],
                        "filter_joiner": "and"
                    }
                },
                "|B|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.time_one_filter, self.instance_filter, self.metric_set_filter if self.metric_set_filter else None],
                        "filter_joiner": "and"
                    }
                }
            },
            "slot_fillers": {
                "EntityReference:0": self.entity_reference,
                "Filter:0": self.time_zero,
                "Filter:1": self.time_one
            }
        }

    def get_average_percent_change_over_time(self) -> Dict:
        return {
            "plan_name": "AggregatePercentChangeOverTime",
            "base_plan": self.base_plan_templates["AggregatePercentChangeOverTime"],
            "access_plans": {
                "|A|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.time_zero_filter, self.metric_set_filter if self.metric_set_filter else None],
                        "filter_joiner": "and"
                    }
                },
                "|B|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.time_one_filter, self.metric_set_filter if self.metric_set_filter else None],
                        "filter_joiner": "and"
                    }
                }
            },
            "slot_fillers": {
                "Analysis:0": "average",
                "EntityReference:0": self.entity_reference,
                "String:0": self.entity_group,
                "Filter:0": self.time_zero,
                "Filter:1": self.time_one
            }
        }

    def get_is_instance_cot_greater_than_average_cot(self) -> Dict:
        return {
            "plan_name": "InstancePercentChangeOverTimeGreaterThanAggregatePercentChangeOverTime",
            "base_plan": self.base_plan_templates["InstancePercentChangeOverTimeGreaterThanAggregatePercentChangeOverTime"],
            "access_plans": {
                "|A|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.time_zero_filter,
                                    self.instance_filter,
                                    self.metric_set_filter if self.metric_set_filter else None],
                        "filter_joiner": "and"
                    }
                },
                "|B|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.time_one_filter,
                                    self.instance_filter,
                                    self.metric_set_filter if self.metric_set_filter else None],
                        "filter_joiner": "and"
                    }
                },
                "|C|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.time_zero_filter,
                                    self.metric_set_filter if self.metric_set_filter else None],
                        "filter_joiner": "and"
                    }
                },
                "|D|": {
                    "access_plan": self.metric_access_plan,
                    "access_plan_filters": {
                        "filters": [self.time_one_filter,
                                    self.metric_set_filter if self.metric_set_filter else None],
                        "filter_joiner": "and"
                    }
                }
            },
            "slot_fillers": {
                "Analysis:0": "average",
                "EntityReference:0": self.entity_reference,
                "Filter:0": self.time_zero,
                "Filter:1": self.time_one,
                "String:0": self.entity_group
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
        prompt = f"Generate a report for {entity_reference} describing how {self.metric_nicename} has changed over time between {self.time_zero} and {self.time_one}{' ' + filter_statement if filter_statement else ''}. " \
                 f"{'Higher' if self.metric_preference_direction == '+inf' else 'Lower'} values are considered better."
        return prompt

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
                  f"In the report, include information about the value of the metric for {entity_reference} at {self.time_zero}, " \
                  f"the value of the metric for {entity_reference} at {self.time_one}, " \
                  f"the percent change between {self.time_zero} and {self.time_one} for {entity_reference}, " \
                  f"the average value of the metric at {self.time_zero} for all {self.entity_name}, " \
                  f"the minimum value of the metric at {self.time_zero} for all {self.entity_name}, " \
                  f"the maximum value of the metric at {self.time_zero} for all {self.entity_name}, " \
                  f"the average value of the metric at {self.time_one} for all {self.entity_name}, " \
                  f"the minimum value of the metric at {self.time_one} for all {self.entity_name}, " \
                  f"the maximum value of the metric at {self.time_one} for all {self.entity_name}, " \
                  f"the percent change between {self.time_zero} and {self.time_one} for all {self.entity_name}, " \
                  f"and whether or not the percent change was greater for {entity_reference} than the percent change for all {self.entity_group}."
        prompt += "\n\n" + self.build_prompting_instructions()
        return prompt
