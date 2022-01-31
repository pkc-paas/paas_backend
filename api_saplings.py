# api_saplings.py

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

saplingFolder = os.path.join(root, 'photos')
saplingThumbFolder = os.path.join(root, 'sapling_thumbs')
os.makedirs(saplingFolder, exist_ok=True)
os.makedirs(saplingThumbFolder, exist_ok=True)


####################

class saplingReq(BaseModel):
    criteria: Optional[str] = None

@app.post("/API/getSaplings", tags=["saplings"])
def getSaplings(r: saplingReq, x_access_key: Optional[str] = Header(None)):
    cf.logmessage("getSaplings api call")
    username, role = findRole(x_access_key)

    s1 = f"""select t1.id, t1.lat, t1.lon, t1.name, t1.group, 
    t1.local_name, t1.botanical_name, t1.planted_date, t1.data_collection_date,
    t1.description, t1.first_photos, t1.confirmed,
    t2.adopted_name, t2.status as adoption_status
    from saplings as t1
    left join (select adopted_name, status, sapling_id from adoptions where status in ('approved','requested')) as t2
    on t1.id = t2.sapling_id
    where (t1.status != 'rejected') OR (t1.status is NULL)
    order by t1.data_collection_date
    """
    df1 = dbconnect.makeQuery(s1, output='df', fillna=False, printit=True)
    
    # df1.to_csv('saplings.csv', index=False)
    if not len(df1):
        cf.logmessage(f"no data")
        raise HTTPException(status_code=400, detail="No data sorry")
    
    # photos: make into array

    def splitter(x):
        if x:
            return x.split(',')
        else:
            return []
    df1['first_photos'] = df1['first_photos'].apply(splitter)
    
    # split it
    df_confirmed = df1[df1['confirmed']==1]
    df_unconfirmed = df1[df1['confirmed']!=1]

    returnD = {
        "message" : f"Retrieved {len(df1)} saplings",
        "data_confirmed" : df_confirmed.to_dict(orient='records')
    }

    # include unconfirmed only if 
    if role in ('admin','saplings_admin','moderator'):
        returnD["data_unconfirmed"] = df_unconfirmed.to_dict(orient='records')
    # # fetch adoption status
    # s2 = f"""select sapling_id, username, adopted_name, status from adoptions where status in ('approved','requested')"""
    # df2 = dbconnect.makeQuery(s2, output='df', fillna=False, printit=True)
    # # process this into json indexed by sapling_id, handle  
    return returnD


#####################
# upload a sapling

# instead of re-reading image from disk, taking the file pointer already loaded in memory.
def compressSapImage(f, idf):
    im = Image.open(f, mode='r')
    im2 = ImageOps.fit(im, (150,200))
    im2.save(os.path.join(saplingThumbFolder, idf))
    return


@app.post("/API/uploadSapling", tags=["saplings"])
def uploadSapling(
        x_access_key: str = Header(...),
        lat: float = Form(...),
        lon: float = Form(...),
        name: str = Form(...),
        data_collection_date: str = Form(...),
        uploadFiles: List[UploadFile] = File(...), 
        group: Optional[str] = Form(None),
        local_name: Optional[str] = Form(None),
        botanical_name: Optional[str] = Form(None),
        planted_date: Optional[str] = Form(None),
        description: Optional[str] = Form(None)
    ):
    # ref: https://github.com/tiangolo/fastapi/issues/854#issuecomment-573965912 for optional form fields etc
    cf.logmessage("uploadSapling api call")

    username, role = authenticate(x_access_key, allowed_roles=['admin','moderator','saplings_admin','saplings_entry'])
    
    # validations:
    # s1 = f"select id from saplings where id='{sapling_id}'"
    # if not dbconnect.makeQuery(s1, output='oneValue'):
    #     raise HTTPException(status_code=400, detail="Invalid sapling_id")

    if not cf.valiDate(data_collection_date):
        raise HTTPException(status_code=400, detail="Invalid observation_date")

    if not cf.validateLL(lat,lon):
        raise HTTPException(status_code=400, detail="Invalid location")

    # to do later: validate or just check if existing the group, local, botanical names

    fileids = []
    sid = cf.makeUID()
    for fN, file1 in enumerate(uploadFiles):
        filename = file1.filename
        extension = filename.split('.')[-1].lower()
        # validate extension
        if extension not in ('jpg','png','jpeg'):
            raise HTTPException(status_code=400, detail="Invalid files")
        
        idf = f"{sid}_{fN+1}.{extension}"
        print(filename, idf)
        with open(os.path.join(saplingFolder, idf),'wb') as f:
            f.write(file1.file.read())
        
        compressSapImage(file1.file, idf) # sending the file pointer and filename
        fileids.append(idf)

    
    iCols = []
    iVals = []

    if group:
        iCols.append('`group`')
        iVals.append(f"'{group}'")

    if local_name:
        iCols.append('local_name')
        iVals.append(f"'{local_name}'")
    
    if botanical_name:
        iCols.append('botanical_name')
        iVals.append(f"'{botanical_name}'")

    if planted_date and cf.valiDate(planted_date):
        iCols.append('planted_date')
        iVals.append(f"'{planted_date}'")
    

    i1 = f"""insert into saplings (id, name, lat, lon, data_collection_date, first_photos, created_on, created_by, confirmed, {','.join(iCols)})
    values ('{sid}', '{name}', {lat},{lon}, '{data_collection_date}', '{','.join(fileids)}', CURRENT_TIMESTAMP, '{username}', 0, {','.join(iVals)})
    """
    i1Count = dbconnect.execSQL(i1, noprint=False)

    returnD = {'status':'success', 'fileids':fileids, 'sid':sid}
    return returnD


# photo fetch api retired, replaced with fastapi's direct static path mounting.
# @app.get("/API/getPhoto", tags=["photos"])
# def getPhoto(f: str):
#     cf.logmessage("getPhoto api call")
#     if os.path.isfile(os.path.join(root, 'photos', f)):
#         return FileResponse(os.path.join(root, 'photos', f))
#     else:
#         cf.logmessage(f"{f} not found")
#         return {
#             "status" : "FAIL",
#             "message" : "not found"
#         }


class processUploadedSaplingReq(BaseModel):
    sapling_id: str = None
    accepted: bool = None

@app.post("/API/processUploadedSapling", tags=["saplings"])
def processUploadedSapling(req: processUploadedSaplingReq, x_access_key: Optional[str] = Header(None)):
    cf.logmessage("getSaplings api call")
    username, role = authenticate(x_access_key, allowed_roles=['admin','moderator','saplings_admin','saplings_entry'])

    sapling_id = req.sapling_id
    accepted = req.accepted

    s1 = f"select * from saplings where id='{sapling_id}'"
    saplingD = dbconnect.makeQuery(s1, output='oneJson')
    if not len(saplingD):
        raise HTTPException(status_code=400, detail="Invalid sapling_id")


    if accepted:
        u1 = f"update saplings set confirmed=1 where sapling_id = '{sapling_id}'"
        u1Count = dbconnect.execSQL(u1)
        if not u1Count:
            raise HTTPException(status_code=400, detail="Not able to update in DB")

    else:
        ui = f"update saplings set status='rejected' where sapling_id = '{sapling_id}'"
        u1Count = dbconnect.execSQL(u1)
        if not u1Count:
            raise HTTPException(status_code=400, detail="Not able to update in DB")

    returnD = {'status':'success'}
    return returnD


########################

class editSaplingReq(BaseModel):
    sapling_id: str
    name: str
    local_name: str = None
    botanical_name: str = None
    planted_date: str = None
    data_collection_date: str = None
    group: str = None
    description: str = None

@app.post("/API/editSapling", tags=["saplings"])
def processUploadedSapling(req: editSaplingReq, x_access_key: Optional[str] = Header(None)):
    cf.logmessage("getSaplings api call")
    username, role = authenticate(x_access_key, allowed_roles=['admin','moderator','saplings_admin','saplings_entry'])

    # fetch existing sapling data
    s1 = f"select * from saplings where id='{req.sapling_id}'"
    existingD = dbconnect.makeQuery(s1, output='oneJson')
    if not existingD:
        raise HTTPException(status_code=400, detail="Invalid sapling_id")

    uHolder = []
    if req.name and req.name != existingD['name']: 
        uHolder.append(f"name = '{req.name}'")
    if req.local_name and req.local_name != existingD['local_name']: 
        uHolder.append(f"local_name = '{req.local_name}'")
    if req.botanical_name and req.botanical_name != existingD['botanical_name']: 
        uHolder.append(f"botanical_name = '{req.botanical_name}'")
    if req.planted_date and req.planted_date != existingD['planted_date']: 
        uHolder.append(f"planted_date = '{req.planted_date}'")
    if req.data_collection_date and req.data_collection_date != existingD['data_collection_date']: 
        uHolder.append(f"data_collection_date = '{req.data_collection_date}'")
    if req.group and req.group != existingD['group']: 
        uHolder.append(f"group = '{req.group}'")
    if req.description and req.description != existingD['description']: 
        uHolder.append(f"description = '{req.description}'")

    if not len(uHolder):
        raise HTTPException(status_code=400, detail="Nothing to update")
        
    uHolder.append(f"modified_on = CURRENT_TIMESTAMP")
    uHolder.append(f"modified_by = '{username}'")

    u1 = f"""update saplings
    set {','.join(uHolder)}
    where id = '{req.sapling_id}'
    """
    u1Count = dbconnect.execSQL(u1)

    if u1Count == 1:
        returnD = {'status': 'success', 'sapling_id': req.sapling_id}
    else:
        raise HTTPException(status_code=400, detail="Not able to update in DB")
