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

from typing import Tuple, List
import sqlalchemy
from core.RingObjects.RingAttribute import RingAttribute
from sqlalchemy.orm import InstrumentedAttribute, Query
from .api.sql_func import nan_cast
from sqlalchemy import func
from sqlalchemy.sql.expression import cast, Label
from core.Analysis.OperationOntology import OperationOntology
from core.Analysis.SQRField import SQRField
from core.api.utils import contains_date_denomination

class DatabaseInterface:
    """
    This class provides an interface to the database and associated SQL Alchemy model classes. It will resolve
    RingObjects/strings to the corresponding SQL Alchemy objects.
    """
    def __init__(self,
                 db: 'DBWrapper'):
        self.db = db

    def get_sqlalchemy_field(self,
                             ring: 'Ring',
                             sqrfield: SQRField,
                             field = None)  -> InstrumentedAttribute:
        """
        Gets the field of the entity for given the attribute.
        :param ring:
        :type ring:
        :param sqrfield:
        :type sqrfield:
        :param field:
        :type field:
        :return:
        :rtype:
        """
        # Get the entity object corresponding to the given entity name
        if sqrfield.entity_name:
            entity_obj = ring.get_entity_by_name(sqrfield.satyrn_entity)
            if sqrfield.satyrn_attribute != 'id':
                date_denomination = contains_date_denomination(sqrfield.satyrn_attribute)
                if date_denomination:
                    attr_obj = entity_obj.attributes[date_denomination.group(1)]
                    model_name = attr_obj.source_table
                    field_name = f'{attr_obj.source_columns[0]}{date_denomination.group(2)}'
                else:
                    attr_obj = entity_obj.attributes[sqrfield.satyrn_attribute]
                    model_name = attr_obj.source_table
                    field_name = attr_obj.source_columns[0]
                # Get the model and field names for the attribute

            else:
                model_name = entity_obj.primary_table
                field_name = entity_obj.id[0] #how do we handle multiple ids here
                attr_obj = None


            if field is None:
                # Get the SQL Alchemy model associated with the model name string
                model = getattr(self.db, model_name)

                # Get the SQL Alchemy object representing this field
                field = getattr(model, field_name)
        else:
            attr_obj = None

        # Finish building the field by applying any necessary transformations to it
        field = self.apply_field_transformations(field, attr_obj)

        return field

    def apply_field_transformations(self,
                                    field: InstrumentedAttribute,
                                    attr_obj: RingAttribute) -> InstrumentedAttribute:
        """
        For the given field, handles null values, adds the analysis op, adds rounding ops, and applies the transform
        :param field:
        :type field:
        :param attr_obj:
        :type attr_obj:
        :return: The field with the transformation applied to it.
        :rtype: InstrumentedAttribute
        """

        # Perform null value handling
        if attr_obj and attr_obj.null_handling and attr_obj.null_handling == "cast":
            field = nan_cast(field, attr_obj.null_value)

        # Add rounding operations to the field object
        if attr_obj:
            if attr_obj.rounding == "True":
                field = func.round(cast(field, sqlalchemy.Numeric), attr_obj.sig_figs)

        return field

    # PENDING: handling multiple columns in the columns of source
    # PENDING: Add "Conversion" to pretty name here (e.g. True/False to other stuff)
    # PENDING: Adding capabilities for multi-table entities (currently being worked on by developers)
    def get_field_label_and_name_and_joins_todo(self,
                                                ring: 'Ring',
                                                sqrfield: SQRField) -> Tuple[Label, list]:
        """
        Returns the SQLAlchemy Label for name, the raw field name, and any joins that must be performed.
        Note: The field.label function converts the Model Attribute's name to the database column name defined in the Satyrn Ring.
              This label can be used as an expression within SQL Alchemy (e.g. for doing comparisons, filters, conditions, etc.)
        Note: "name" is the name of the Attribute from the SQL Alchemy Model.
        Note: This is the function formerly known as "_get()".
        :param ring:
        :type ring:
        :param sqrfield:
        :type sqrfield:
        :return:
        :rtype:
        """

        # Get all of the joins required for to query this attribute
        joins_todo = ring.get_attribute_joins(sqrfield.satyrn_entity, sqrfield.satyrn_attribute)

        # Get the SQL Alchemy field for this attribute
        field = ring.db_interface.get_sqlalchemy_field(ring, sqrfield)

        # Convert the field to its label
        return field.label(sqrfield.column_name), joins_todo

    def get_field_label_and_joins_for_operation(self,
                                                ring: 'Ring',
                                                op_sqrfield: SQRField,
                                                ontology: OperationOntology,
                                                subqueries: List[Query]) -> Tuple[Label, list]:
        """
        Returns the SQLAlchemy Label for name, the raw field name, and any joins that must be performed.
        Note: The field.label function converts the Model Attribute's name to the database column name defined in the Satyrn Ring.
              This label can be used as an expression within SQL Alchemy (e.g. for doing comparisons, filters, conditions, etc.)
        Note: "name" is the name of the Attribute from the SQL Alchemy Model.
        Note: This is the function formerly known as "_get()".
        :param ring:
        :type ring:
        :param sqrfield:
        :type sqrfield:
        :param ontology:
        :type ontology:
        :return:
        :rtype:
        """

        op = ontology.resolve_operation(op_sqrfield.field['type'])
        joins_todo = set()
        fields = []
        for sqrfield in op_sqrfield.field['arguments']:
            # Get all of the joins required for to query this attribute
            if type(sqrfield) != SQRField:
                fields.append(sqrfield)
            elif not sqrfield.entity_name: # field is being retrieved from a return
                if type(sqrfield.field) == SQRField:
                    # Get the SQL Alchemy field for this attribute
                    field = subqueries[sqrfield.field.subplan_name].columns[sqrfield.field.column_name]

                    fields.append(ring.db_interface.get_sqlalchemy_field(ring, sqrfield, field=field))
                elif type(sqrfield.field) == dict:
                    field, new_joins_todo = self.get_field_label_and_joins_for_operation(ring, sqrfield, ontology, subqueries)
                    joins_todo.update(new_joins_todo)
                    fields.append(field)
                else:
                    raise Exception("This shouldn't happen!")
            else:
                joins_todo.update(ring.get_attribute_joins(sqrfield.satyrn_entity, sqrfield.satyrn_attribute))

                # Get the SQL Alchemy field for this attribute
                fields.append(ring.db_interface.get_sqlalchemy_field(ring, sqrfield))

        # Add the operation to the field object
        op_field = op.sqlalchemy_op(fields, ring.get_db_type())
        if op.name in ['average', 'stddev', 'divide', 'percent_change']:
            op_field = func.round(cast(op_field, sqlalchemy.Numeric), 2)

        # Convert the field to its label
        return op_field.label(op_sqrfield.column_name), joins_todo
