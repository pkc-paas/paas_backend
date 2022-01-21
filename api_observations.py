# api_observations.py

from typing import Optional, List
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi import HTTPException, Header, File, UploadFile, Form
import secrets, io, os
import pandas as pd
from PIL import Image, ImageOps

from paas_launch import app
import commonfuncs as cf
import dbconnect
from api_users import authenticate


root = os.path.dirname(__file__)
observationsFolder = os.path.join(root, 'observation_files')
os.makedirs(observationsFolder, exist_ok=True)

observationsThumbnailsFolder = os.path.join(root, 'observation_thumbs')
os.makedirs(observationsThumbnailsFolder, exist_ok=True)

###############

class viewObservations_payload(BaseModel):
    saplingsList: List[str]
    # action: str

@app.post("/API/viewObservations", tags=["observations"])
def viewObservations(req: viewObservations_payload, x_access_key: Optional[str] = Header(None)):
    cf.logmessage("viewObservations api call")
    
    # username, role = authenticate(x_access_key, allowed_roles=['admin','moderator'])
    
    if not len(req.idsList):
        raise HTTPException(status_code=400, detail="No inputs")
    
    timestamp = cf.getTime()
    date1 = cf.getDate()

    saplingsListSQL = cf.quoteNcomma(req.saplingsList)
    s1 = f"""select * from observations where id in ({saplingsListSQL})
    order by sapling_id, observation_date
    """
    df1 = dbconnect.makeQuery(s1, output='df', noprint=False)

    returnD = {'status':'success'}
    if len(df1):
        returnD['observations'] = df1.to_dict(orient='records')
    else:
        returnD['observations'] = []
    return returnD


############


# instead of re-reading image from disk, taking the file pointer already loaded in memory.
def compressObsImage(f, idf):
    im = Image.open(f, mode='r')
    im2 = ImageOps.fit(im, (150,200))
    im2.save(os.path.join(observationsThumbnailsFolder, idf))
    return


@app.post("/API/postObservation", tags=["observations"])
def postObservation(
        files: List[UploadFile] = File(...), 
        sapling_id: str = Form(...),
        observation_date: str = Form(...),
        growth_status: Optional[str] = Form(None),
        health_status: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        x_access_key: Optional[str] = Header(None)
    ):
    # ref: https://github.com/tiangolo/fastapi/issues/854#issuecomment-573965912 for optional form fields etc
    cf.logmessage("postObservation api call")

    # username, role = authenticate(x_access_key, allowed_roles=['admin','moderator','sponsor','saplings_admin','saplings_entry'])
    
    # validations:
    s1 = f"select id from saplings where id='{sapling_id}'"
    if not dbconnect.makeQuery(s1, output='oneValue'):
        raise HTTPException(status_code=400, detail="Invalid sapling_id")

    if not cf.valiDate(observation_date):
        raise HTTPException(status_code=400, detail="Invalid observation_date")

    print(f"growth_status: {growth_status} | health_status: {health_status} | description: {description}")
    
    fileids = []
    oid = cf.makeUID()
    for fN, file1 in enumerate(files):
        filename = file1.filename
        extension = filename.split('.')[-1].lower()
        # validate extension
        if extension not in ('jpg','png','jpeg'):
            raise HTTPException(status_code=400, detail="Invalid files")
        
        idf = f"{oid}_{fN+1}.{extension}"
        print(filename, idf)
        with open(os.path.join(observationsFolder, idf),'wb') as f:
            f.write(file1.file.read())
        
        compressObsImage(file1.file, idf) # sending the file pointer and filename
        fileids.append(idf)

    
    iCols = []
    iVals = []
    if growth_status:
        iCols.append('growth_status')
        iVals.append(f"'{growth_status}'")

    if health_status:
        iCols.append('health_status')
        iVals.append(f"'{health_status}'")
    
    if description:
        iCols.append('description')
        iVals.append(f"'{description}'")

    i1 = f"""insert into observations (id, sapling_id, photo_id, observation_date, created_on, {','.join(iCols)})
    values ('{oid}', '{sapling_id}', '{','.join(fileids)}', '{observation_date}', CURRENT_TIMESTAMP, {','.join(iVals)})
    """
    i1Count = dbconnect.execSQL(i1, noprint=False)

    returnD = {'status':'success', 'fileids':fileids, 'oid':oid}
    return returnD


############

