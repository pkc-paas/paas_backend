# api_observations.py

from typing import Optional, List
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi import HTTPException, Header, File, UploadFile, Form
import secrets, io, os
import pandas as pd
from PIL import Image, ImageOps
from math import ceil

from paas_launch import app
import commonfuncs as cf
import dbconnect
from api_users import authenticate


root = os.path.dirname(__file__)
observationsFolder = os.path.join(root, 'observation_files')
observationsThumbnailsFolder = os.path.join(root, 'observation_thumbs')
# os.makedirs(observationsFolder, exist_ok=True)
# os.makedirs(observationsThumbnailsFolder, exist_ok=True)


###############

class viewObservations_payload(BaseModel):
    saplingsList: List[str]
    # action: str

@app.post("/API/viewObservations", tags=["observations"])
def viewObservations(req: viewObservations_payload):
    cf.logmessage("viewObservations api call")
    
    # username, role = authenticate(x_access_key, allowed_roles=['admin','moderator'])
    
    if not len(req.saplingsList):
        raise HTTPException(status_code=400, detail="No inputs")
    
    timestamp = cf.getTime()
    date1 = cf.getDate()

    saplingsListSQL = cf.quoteNcomma(req.saplingsList)
    s1 = f"""select * from observations where sapling_id in ({saplingsListSQL})
    order by sapling_id, observation_date, created_on
    """
    df1 = dbconnect.makeQuery(s1, output='df')

    returnD = {'status':'success'}
    if len(df1):
        returnD['observations'] = df1.to_dict(orient='records')
    else:
        returnD['observations'] = []
    return returnD


@app.get("/API/listObservations", tags=["observations"])
def listObservations(page: Optional[int] = 1, sapling_id: Optional[str]=None ):
    cf.logmessage(f"listObservations api call, page: {page}")
    if page < 1:
        raise HTTPException(status_code=400, detail="Invalid page num")

    pageSize = 50
    returnD = {'status':'success'}
    returnD['pageSize'] = pageSize

    s2 = """select count(*) from observations"""
    
    if sapling_id:
        print(f"Loading observations only for sapling_id = '{sapling_id}'")
        whereClause = f"where t2.id = '{sapling_id}'"
        s2 = f"""select count(*)
        from observations
        where sapling_id = '{sapling_id}'
        """
    else: 
        whereClause = ''
    
    obsCount = dbconnect.makeQuery(s2, output='oneValue')

    returnD['total_pages'] = ceil( obsCount / pageSize)


    if (page > 1) and (page > returnD['total_pages']):
        raise HTTPException(status_code=400, detail="exceeded pages")

    # handle case where no observations
    if obsCount == 0:
        returnD['observations'] = []
        returnD['saplingsLookup'] = {}
        return returnD


    s1 = f"""select t1.* , t2.name as sapling_name
    from observations as t1 
    left join saplings as t2
    on t1.sapling_id = t2.id
    {whereClause}
    order by t1.observation_date desc
    limit {(page-1)*pageSize},{pageSize}
    """
    df1 = dbconnect.makeQuery(s1, output='df')
    returnD['observations'] = df1.to_dict(orient='records')


    # get unique sapling ids list and fetch the location etc
    saplingsList= df1['sapling_id'].unique().tolist()
    saplingsListSQL = cf.quoteNcomma(saplingsList)
    s2 = f"""select t1.*
    from saplings as t1
    where id in ({saplingsListSQL})
    order by id
    """
    df2 = dbconnect.makeQuery(s2, output='df').set_index('id')

    returnD['saplingsLookup'] = df2.to_dict(orient='index')

    return returnD

############


# instead of re-reading image from disk, taking the file pointer already loaded in memory.
def saveObsImage(f, idf):
    im = Image.open(f, mode='r')
    im1 = ImageOps.exif_transpose(im) # auto-rotate mobile photos. from https://stackoverflow.com/a/63798032/4355695
    
    # save thumbnail
    im2 = ImageOps.fit(im1, (150,200))
    im2.save(os.path.join(observationsThumbnailsFolder, idf))

    # save picture, but downsized to 2000x2000 dimensions (in case its big) to optimize storage
    w, h = im1.size
    if(h > 2000 or w > 2000):
        im3 = ImageOps.contain(im1, (2000,2000))
        im3.save(os.path.join(observationsFolder, idf))
    else:
        im1.save(os.path.join(observationsFolder, idf))

    return


@app.post("/API/postObservation", tags=["observations"])
def postObservation(
        uploadFiles: List[UploadFile] = File(...), 
        sapling_id: str = Form(...),
        observation_date: str = Form(...),
        growth_status: Optional[str] = Form(None),
        health_status: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        x_access_key: Optional[str] = Header(None)
    ):
    # ref: https://github.com/tiangolo/fastapi/issues/854#issuecomment-573965912 for optional form fields etc
    cf.logmessage("postObservation api call")

    username, role = authenticate(x_access_key, allowed_roles=['admin','moderator','sponsor','saplings_admin','saplings_entry'])
    
    # validations:
    s1 = f"select id from saplings where id='{sapling_id}'"
    if not dbconnect.makeQuery(s1, output='oneValue'):
        raise HTTPException(status_code=400, detail="Invalid sapling_id")

    if not cf.valiDate(observation_date):
        raise HTTPException(status_code=400, detail="Invalid observation_date")

    print(f"growth_status: {growth_status} | health_status: {health_status} | description: {description}")
    
    fileids = []
    oid = cf.makeUID()
    for fN, file1 in enumerate(uploadFiles):
        filename = file1.filename
        extension = filename.split('.')[-1].lower()
        # validate extension
        if extension not in ('jpg','png','jpeg'):
            raise HTTPException(status_code=400, detail="Invalid files")
        
        idf = f"{oid}_{fN+1}.{extension}"
        # print(filename, idf)
        # with open(os.path.join(observationsFolder, idf),'wb') as f:
        #     f.write(file1.file.read())
        
        saveObsImage(file1.file, idf) # sending the file pointer and filename
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


    columnsEnd = ''
    if len(iCols): columnsEnd = f", {','.join(iCols)}"
    valuesEnd = ''
    if len(iVals): valuesEnd = f", {','.join(iVals)}"
    i1 = f"""insert into observations (id, sapling_id, photo_id, observation_date, created_on {columnsEnd})
    values ('{oid}', '{sapling_id}', '{','.join(fileids)}', '{observation_date}', CURRENT_TIMESTAMP {valuesEnd})
    """
    i1Count = dbconnect.execSQL(i1, noprint=False)

    returnD = {'status':'success', 'fileids':fileids, 'oid':oid}
    return returnD


############


class saplingInfo4ObsReq(BaseModel):
    sapling_id: str

@app.post("/API/saplingInfo4Obs", tags=["observations"])
def saplingInfo4Obs(req: saplingInfo4ObsReq):
    cf.logmessage("saplingInfo4Obs api call")

    # fetch existing sapling data
    s1 = f"select * from saplings where id='{req.sapling_id}'"
    saplingD = dbconnect.makeQuery(s1, output='oneJson')

    if not len(saplingD):
        raise HTTPException(status_code=400, detail="Sapling not found")

    saplingD['past_observations'] = {}
    s2 = f"""select id, observation_date from observations where sapling_id='{req.sapling_id}'
    order by observation_date
    """
    df1 = dbconnect.makeQuery(s2, output='df')
    if len(df1):
        saplingD['past_observations']['num'] = len(df1)
        saplingD['past_observations']['last_date'] = str(df1['observation_date'].tolist()[-1])
    else:
        saplingD['past_observations']['num'] = 0
    
    returnD = {'status':'success'}
    returnD['sapling_data'] = saplingD

    return returnD
