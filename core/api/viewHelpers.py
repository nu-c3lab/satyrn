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

from datetime import datetime
from functools import wraps
import json
import os
from typing import Dict, Union, List

from flask import current_app, request, Request
import requests

from ..RingCompiler import compile_ring, Ring

app = current_app # this is now the same app instance as defined in appBundler.py

# a decorator for checking API keys
# API key set flatfootedly via env in appBundler.py for now
# requires that every call to the API has a get param of key=(apikey) appended to it
# basic implementation -- most use cases will require this is updated to pass via request header
def api_key_check(innerfunc):
    @wraps(innerfunc)
    def decfunc(*args, **kwargs):
        if "ENV" in app.config and app.config["ENV"] in ["development", "dev"]:
            # we can bypass when running locally for ease of dev
            pass
        elif not request.headers.get("x-api-key"):
            return error_gen("API key required")
        elif request.headers.get("x-api-key") != app.config["API_KEY"]:
            return error_gen("Incorrect API key")
        return innerfunc(*args, **kwargs)
    return decfunc

def error_gen(msg):
    return json.dumps({
        "success": False,
        "message": str(msg)
    })

def format_date(dte: str) -> datetime:
    """
    Removes timezone info and converts to datetime object.
    :param dte: The date string to clean.
    :type dte: str
    :return: The cleaned datetime.
    :rtype: datetime
    """
    # Fri Oct 29 2021 00:00:00 GMT-0500 (Central Daylight Time)
    dte = dte.split("-")[0]
    return datetime.strptime(dte, '%a %b %d %Y %H:%M:%S %Z') if dte != "null" else None

def clean_date(dte: Union[str, datetime]) -> datetime:
    """
    Ensures the date is well formatted as a datetime.
    :param dte: An object representing a date.
    :type dte: str or datetime
    :return: The cleaned date.
    :rtype: datetime
    """
    if type(dte) == datetime:
        return dte
    elif dte.find("(") != -1:
        return format_date(dte)
    else:
        if "T" in dte:
            dte = dte.split("T")[0]
        return datetime.strptime(dte, '%Y-%m-%d') if dte != "null" else None

def clean_float(num) -> float:
    """
    Converts the given object to a float and returns None if unable to do so.
    :param num: An object that should ideally be convertable to a float.
    :type num: The object to convert.
    :return: The number as a float.
    :rtype: float
    """
    try:
        return float(num)
    except ValueError:
        return None

def clean_int(num) -> int:
    """
    Converts the given object to an int and returns None if unable to do so.
    :param num: An object that should ideally be convertable to an int.
    :type num: The object to convert.
    :return: The number as an integer.
    :rtype: int
    """
    try:
        return int(num)
    except ValueError:
        return None

############################################################
# RING HELPERS
############################################################

def get_or_create_ring(ring_id: str,
                       version: str=None,
                       force_refresh: bool=False) -> Ring:
    """
    Used to get or create ring as necessary.
    :param ring_id: The ID of the ring to get.
    :type ring_id: str
    :param version: The ring version.
    :type version: str
    :param force_refresh: Force the ring to be retrieved/built via the API.
    :type force_refresh: bool
    :return: The ring and the associated extractor.
    :rtype: Tuple of Ring, RingExtractor
    """

    version = int(version) if version else version
    if (ring_id not in app.rings) or (version and version not in app.rings.get(ring_id, {})) or force_refresh:
        try:
            get_ring_from_service(ring_id, version)
        except:
            msg = "Ring with id {} ".format(ring_id)
            msg += "and version number {} ".format(version) if version is not None else "at any version number "
            msg += "could not be loaded from service. This is likely either because a ring with this ID/version number can't be found or because the asset service is down."
            return {"success": False, "message": msg}, None
    if not version:
        # get the highest version number available (mirrors behavior of the get)
        versions = sorted(app.rings[ring_id].keys())
        version = versions[-1:][0]
    return app.rings[ring_id][version]

def get_ring(ring_id: str,
             version: int=None) -> Ring:
    """
    Retrieves/builds the specified ring.
    :param ring_id: The ID of the ring.
    :type ring_id: str
    :param version: The ring version.
    :type version: int
    :return: The ring configuration object.
    :rtype: Ring
    """
    ring, ring_extractor = get_or_create_ring(ring_id, version)
    return ring

def get_ring_from_service(ring_id: str,
                          version: int=None) -> None:
    """
    Gets/builds the ring via the API. Attaches it to the app.
    :param ring_id: The ID of the ring.
    :type ring_id: str
    :param version: The ring version.
    :type version: int
    :return: None
    :rtype: None
    """

    headers = {"x-api-key": app.config["UX_SERVICE_API_KEY"]}
    if version:
        request = requests.get(os.path.join(app.ux_service_api, "rings", ring_id, str(version)), headers=headers)
    else:
        # get the latest...
        request = requests.get(os.path.join(app.ux_service_api, "rings", ring_id), headers=headers)
    print("getting ring", flush=True)
    try:
        requestJSON = request.json()
        ring_config = requestJSON["data"]["ring"]
    except:
        print("Issue loading ring...", flush=True)

    if type(ring_config) == str:
        ring_config = json.loads(ring_config)
    ring = compile_ring(ring_config, in_type="json")
    if not ring.id in app.rings:
        app.rings[ring.id] = {}
        app.ring_extractors[ring.id] = {}
    if not version:
        version = ring.version
    app.rings[ring.id][version] = ring
