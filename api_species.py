# api_species.py

from typing import Optional, List
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi import HTTPException, Header, File, UploadFile, Form
import secrets, os
from PIL import Image, ImageOps

from paas_launch import app
import commonfuncs as cf
import dbconnect
from api_users import authenticate, findRole


root = os.path.dirname(__file__)

####################

@app.get("/API/speciesList", tags=["species"])
def speciesList(moreCols:Optional[str]=None ):
    cf.logmessage("speciesList api call")
    returnD = {'status':'success'}

    colsList = ['id', 'local_name', 'botanical_name']
    if moreCols:
        colsList.extend(moreCols.split(','))

    # to do: validation, get rid of invalid column names and keep the valid ones
    
    s1 = f"""select {','.join(colsList)} from species
    order by local_name
    """
    
    list1 = dbconnect.makeQuery(s1, output='list')
    returnD['species'] = list1
    return returnD
