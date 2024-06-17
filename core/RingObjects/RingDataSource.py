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
import datetime
import platform
import pandas as pd
from dateutil import parser
from functools import reduce
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.event import listen
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.base import Engine

from .RingJoin import RingJoin
from .RingObject import RingObject
from ..RingDB import RingDB

try:
    from core.satyrnBundler import app
except:
    from ..satyrnBundler import app

def connect_to_extensions(engine: Engine):

    os_type = platform.system()
    os_type_dct = {
        "Windows": ".dll",
        "Linux": ".so",
        "Darwin": ".dylib",
    }
    if os_type not in os_type_dct:
        print(f"unknown os_type: {os_type}")
        print("will not try to do extensions, be wary of some sqlite functionality")
        return False

    def load_extension(dbapi_conn, unused):
        # Note: unused needs to be here for the SQLAlchemy listen() function to work properly

        os_type = platform.system()
        os_type_dct = {
            "Windows": ".dll",
            "Linux": ".so",
            "Darwin": ".dylib",
        }
        mypath = os.environ.get("SATYRN_ROOT_DIR") + "/" +"core" + "/" +"sqlite_extensions" + "/"
        onlyfiles = [f for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f)) and f.endswith(os_type_dct[os_type])]
        for thefile in onlyfiles:
            file_name = os.path.join(mypath, thefile)
            dbapi_conn.enable_load_extension(True)
            dbapi_conn.load_extension(file_name)
            dbapi_conn.enable_load_extension(False)

    with app.app_context():
        listen(engine, 'connect', load_extension)

    return True

class RingDataSource(RingObject):
    """
    Database schema and connection to the actual data.
    """

    def __init__(self,
                 base=None):

        # Set default values
        self.type = 'sqlite'

        # Initialize other properties
        self.connection_string = None
        self.tables = None
        self.joins = []
        self.eng = None
        self.session = None

        # # Tie in the base
        self.base = base if base else declarative_base()

        self.error_set = set()

    def parse(self,
              source_config: dict) -> None:
        self.type = source_config.get('type')
        if self.type in ["sqlite", "csv"]:
            ffl = os.environ.get("FLAT_FILE_LOC", "/")
            self.connection_string = os.path.join(ffl, source_config.get('connectionString'))
        else:
            self.connection_string = source_config.get('connectionString')
        self.tables = source_config.get('tables')
        self.parse_joins(source_config)

    def parse_joins(self,
                    source_config: dict) -> None:
        if 'joins' in source_config:
            joins = source_config['joins']
            for join in joins:
                join_object = RingJoin()
                join_object.parse(join)
                self.joins.append(join_object)

    def construct(self):
        source = {}
        self.safe_insert('type', self.type, source)
        self.safe_insert('connectionString', self.connection_string, source )
        self.safe_insert('tables', self.tables, source)
        self.safe_insert('joins', list(map((lambda join: join.construct()), self.joins)), source)
        return source

    def is_valid(self):
        if self.type == None:
            self.error_set.add("Ring Source 'type' is missing.")
        if self.connection_string == None:
            self.error_set.add("Ring Source 'connection string' is missing.")
        if self.tables == None:
            self.error_set.add("Ring Source 'tables' is missing.")
        valid =  bool(self.type and self.connection_string and self.tables)
        for table in self.tables:
            if 'name' not in table:
                self.error_set.add("Ring Source table's 'name' is missing.")
            if 'primaryKey' not in table:
                self.error_set.add("Ring Source table's 'primaryKey' is missing.")
            if type(table['primaryKey']) != dict:
                self.error_set.add("Ring source table's 'primaryKey' is the wrong type. It should be a dict mapping the column name to the column type.")
        if self.joins:
            valid = valid and reduce((lambda x, y: x and y), map((lambda x: x.is_valid()[0]), self.joins))
            if valid == False:
                self.error_set.add("There is an issue with the validity of the joins.")
        if len(self.error_set) == 0:
            return (True, {})
        else:
            ## will return a string of errors
            errorString = ' '.join(self.error_set)
            return (False, errorString)

    def make_connection(self,
                        db: RingDB):
        """

        :param db: The wrapper object that will provide access to the database.
        :type db: RingDB
        :return: The database engine and the session used to make queries
        :rtype:
        """
        if self.type == "sqlite":
            self.eng = create_engine("sqlite:///{}".format(self.connection_string))
            connect_to_extensions(self.eng)
            self.session = sessionmaker(bind=self.eng)
        elif self.type == "csv":
            self.eng, self.session = self.csv_file_pathway(self.connection_string, db)
        else:
            self.eng = create_engine(self.connection_string, pool_size=1, max_overflow=19)
            self.session = sessionmaker(bind=self.eng)
        return self.eng, self.session


    def csv_file_pathway(self,
                         csv_path,
                         db,
                         satyrn_file="satyrn_sql_file.db"):
        # Grab the csv file
        # Grab thedb as a whole

        # NOTE: assumptions we make
        # We assume that  the csv_path is a path to the folder with csvs
        # we assume that the "table names" for each model are the same
        # as the table name for each csv (e..g model "contribution" has "contribution.csv")
        # We assume that all the columns have headers, same headers as column_name
        # We will save the resulting sql file to the same csv_path
        # PENDING: checking if a populated sql file exists

        # if condition to check if all stuff has been created
        path = os.path.join(self.connection_string, satyrn_file)
        if os.path.isfile(path):
            self.eng = create_engine("sqlite:///" + path)
            connect_to_extensions(self.eng)
            self.session = sessionmaker(bind=self.eng)
            return self.eng, self.session
        else:
            self.eng = create_engine("sqlite:///" + path)
            connect_to_extensions(self.eng)
            self.session = sessionmaker(bind=self.eng)

        def cast_value(value,
                       tpe,
                       dateparse=None):
            if tpe == "INTEGER":
                try:
                    return int(value)
                except:
                    return None

            elif tpe == "FLOAT":
                try:
                    return float(value)
                except:
                    return None

            elif tpe == "VARCHAR":
                try:
                    return str(value)
                except:
                    return None

            elif tpe == "DATETIME":
                try:
                    if dateparse:
                        return datetime.datetime.strptime(value, dateparse)
                    else:
                        return parser.parse(value)
                except:
                    return None

            elif tpe == "DATE":
                try:
                    if value:
                        if dateparse:
                            return datetime.datetime.strptime(value, dateparse)
                        else:
                            return parser.parse(value)
                    else:
                        raise ValueError('Value was None, will return None')
                except:
                    return None
            elif tpe == "BOOLEAN":
                return bool(value)
            else:
                print("unrecognized tpe")
                return value

        for model_name in db.__dict__.keys():
            model_class = getattr(db, model_name)
            file_name = "{}{}.csv".format(self.connection_string, model_name)
            df = pd.read_csv(file_name)
            model_list = []
            model_class.metadata.create_all(self.eng)

            for idx, row in df.iterrows():
                new_model = model_class()
                for key in model_class.__dict__.keys():
                    if key[0] != "_" and key in row:
                        # Need to do parsing properly here
                        attr = getattr(model_class, key)
                        tpe = attr.type
                        value = cast_value(row[key], tpe.__str__())
                        setattr(new_model, key, value)

                model_list.append(new_model)

            with self.session.begin() as session:
                session.add_all(model_list)

        return self.eng, self.session
