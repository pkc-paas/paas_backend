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

####################

class saplingReq(BaseModel):
    tenant_id: Optional[int] = 1

@app.post("/API/getSaplings", tags=["saplings"])
def getSaplings(r: saplingReq, x_access_key: Optional[str] = Header(None)):
    cf.logmessage("getSaplings api call")
    user_id, role = findRole(x_access_key)

    s1 = f"""select t1.sapling_id, t1.name,
    ST_Y(t1.geometry) as lat, ST_X(t1.geometry) as lon, 
    t1.planted_date, t1.data_collection_date, t1.confirmed, t1.species_id,
    t1.height, t1.canopy, t1.girth_1m,
    t1.descr, t1.photos, t1.tags,
    t2.adopted_name, t2.adoption_status,
    t3.local_name, t3.botanical_name
    from saplings as t1
    left join (select adopted_name, adoption_status, sapling_id from adoptions where adoption_status in ('approved','requested')) as t2
    on t1.sapling_id = t2.sapling_id
    left join species as t3
    on t1.species_id = t3.species_id
    where t1.tenant_id = {r.tenant_id}
    order by t1.data_collection_date
    """
    # where (t1.status != 'rejected') OR (t1.status is NULL)
    
    df1 = dbconnect.makeQuery(s1, output='df', fillna=False)
    
    # df1.to_csv('saplings.csv', index=False)
    if not len(df1):
        cf.logmessage(f"no data")
        raise HTTPException(status_code=400, detail="No data sorry")
    
    # photos: make into array - already done
    # def splitter(x):
    #     if x:
    #         return x.split(',')
    #     else:
    #         return []
    # df1['first_photos'] = df1['first_photos'].apply(splitter)
    
    # create a combined column for searching
    df1['search'] = df1.fillna('').apply(lambda x: f"{x['name']} {x['sapling_id']} {x['local_name']} {x['botanical_name']} {x['adopted_name']}".strip(), axis=1)

    # print(df1['confirmed'])

    # df1.drop(['id', 'lat', 'lon', 'name', 'group', 'local_name', 'botanical_name', 'planted_date', 'data_collection_date', 'description', 'first_photos', 'height', 'canopy', 'girth_1m', 'adopted_name', 'adoption_status', 'search'], axis=1, inplace=True)

    # split it
    df_confirmed = df1[df1['confirmed']]
    df_unconfirmed = df1[~df1['confirmed']]

    returnD = {
        "message" : f"Retrieved {len(df1)} saplings",
        "data_confirmed" : df_confirmed.to_dict(orient='records')
    }

    # # include unconfirmed only if 
    # if role in ('admin','saplings_admin','moderator'):
    returnD["data_unconfirmed"] = df_unconfirmed.to_dict(orient='records')
    # # fetch adoption status
    # s2 = f"""select sapling_id, username, adopted_name, status from adoptions where status in ('approved','requested')"""
    # df2 = dbconnect.makeQuery(s2, output='df', fillna=False, printit=True)
    # # process this into json indexed by sapling_id, handle  
    return returnD


#####################
# upload a sapling

# instead of re-reading image from disk, taking the file pointer already loaded in memory.
def saveSapImage(f, idf):
    im = Image.open(f, mode='r')
    im1 = ImageOps.exif_transpose(im) # auto-rotate mobile photos. from https://stackoverflow.com/a/63798032/4355695
    
    # save thumbnail
    im2 = ImageOps.fit(im1, (150,200))
    im2.save(os.path.join(cf.folders['sapling_thumbs'], idf))
    
    # save picture, but downsize to within 2000x2000px in case its big, to optimize storage
    w, h = im1.size
    if(h > 2000 or w > 2000):
        im3 = ImageOps.contain(im1, (2000,2000))
        im3.save(os.path.join(cf.folders['sapling_files'], idf))
    else:
        im1.save(os.path.join(cf.folders['sapling_files'], idf))
    
    return


@app.post("/API/uploadSapling", tags=["saplings"])
def uploadSapling(
        x_access_key: str = Header(...),
        lat: float = Form(...),
        lon: float = Form(...),
        name: str = Form(...),
        data_collection_date: str = Form(...),
        uploadFiles: List[UploadFile] = File(...), 
        species_id: Optional[int] = Form(None),
        # group: Optional[str] = Form(None),
        # local_name: Optional[str] = Form(None),
        # botanical_name: Optional[str] = Form(None),
        planted_date: Optional[str] = Form(None),
        descr: Optional[str] = Form(None),
        height: Optional[float] = Form(None),
        canopy: Optional[float] = Form(None),
        girth_1m: Optional[float] = Form(None)
    ):
    # t1.height, t1.canopy, t1.girth_1m,
    # ref: https://github.com/tiangolo/fastapi/issues/854#issuecomment-573965912 for optional form fields etc
    cf.logmessage("uploadSapling api call")

    tenant, user_id, role = authenticate(x_access_key, allowed_roles=['admin','moderator','saplings_admin','saplings_entry'])
    
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
        # print(filename, idf)
        # with open(os.path.join(saplingFolder, idf),'wb') as f:
        #     f.write(file1.file.read())
        
        saveSapImage(file1.file, idf) # sending the file pointer and filename
        fileids.append(idf)

    
    iCols = []
    iVals = []

    iCols.append('tenant_id')
    iVals.append(f"{tenant}")

    iCols.append('created_by')
    iVals.append(f"{user_id}")

    iCols.append('geometry')
    iVals.append(f"ST_GeomFromText('POINT({lon} {lat})', 4326 )")
    
    iCols.append('name')
    iVals.append(f"'{name}'")

    iCols.append('photos')
    iVals.append(f"{cf.arraySQL(fileids)}")

    if species_id:
        iCols.append('species_id')
        iVals.append(f"{species_id}")

    if descr:
        iCols.append('descr')
        iVals.append(f"'{descr}'")
    
    if planted_date and cf.valiDate(planted_date):
        iCols.append('planted_date')
        iVals.append(f"'{planted_date}'")
    
    if height:
        iCols.append('height')
        iVals.append(f"{height}")

    if canopy:
        iCols.append('canopy')
        iVals.append(f"{canopy}")

    if girth_1m:
        iCols.append('girth_1m')
        iVals.append(f"{girth_1m}")

    # auto-confirm for admins and saplings_admin users
    iCols.append('confirmed')
    if role in ('admin', 'saplings_admin'):
        iVals.append(f"TRUE")
        cf.logmessage(f"auto-confirming the sapling upload as its by {role}")
        # possible: can also whitelist selected users
    else:
        iVals.append(f"FALSE")

    i1 = f"""insert into saplings ({','.join(iCols)})
    values ({','.join(iVals)})
    """
    i1Count = dbconnect.execSQL(i1, noprint=False)
    if not i1Count:
        raise HTTPException(status_code=500, detail="Unable to upload this to DB, please try again or contact admin.")

    # Q: do we need to give the sapling_id?
    returnD = {'status':'success', 'fileids':fileids, 'sid':sid}
    return returnD


class processUploadedSaplingReq(BaseModel):
    sapling_id: int = None
    accepted: bool = None

@app.post("/API/processUploadedSapling", tags=["saplings"])
def processUploadedSapling(req: processUploadedSaplingReq, x_access_key: Optional[str] = Header(None)):
    cf.logmessage("processUploadedSapling api call")
    
    tenant, user_id, role = authenticate(x_access_key, allowed_roles=['admin','moderator','saplings_admin'])

    sapling_id = req.sapling_id
    accepted = req.accepted

    s1 = f"select * from saplings where sapling_id = {sapling_id}"
    saplingD = dbconnect.makeQuery(s1, output='oneJson')
    if not len(saplingD):
        raise HTTPException(status_code=400, detail="Invalid sapling_id")


    if accepted:
        u1 = f"update saplings set confirmed=TRUE where sapling_id = {sapling_id}"
        u1Count = dbconnect.execSQL(u1)
        if not u1Count:
            raise HTTPException(status_code=500, detail="Not able to update in DB")


    else:
        u1 = f"""update saplings 
        set confirmed=FALSE, 
        tags = jsonb_set(tags, '{status}','"rejected"')
        where id = '{sapling_id}'
        and tenant_id = {tenant}
        """
        u1Count = dbconnect.execSQL(u1)
        if not u1Count:
            raise HTTPException(status_code=500, detail="Not able to update in DB")
        # else:
            # to do: remove attached images - or do cleanup tasks later

    returnD = {'status':'success'}
    return returnD


########################

class editSaplingReq(BaseModel):
    sapling_id: int
    name: str = None
    species_id: int = None
    planted_date: str = None
    data_collection_date: str = None
    descr: str = None
    height: float = None
    canopy: float = None
    girth_1m: float = None
    # photos: List[str]
    lat: float = None
    lon: float = None

@app.post("/API/editSapling", tags=["saplings"])
def editSapling(req: editSaplingReq, x_access_key: Optional[str] = Header(None)):
    cf.logmessage("editSapling api call")
    
    tenant, user_id, role = authenticate(x_access_key, allowed_roles=['admin','moderator','saplings_admin','saplings_entry'])

    # fetch existing sapling data
    s1 = f"""select t1.*, ST_Y(t1.geometry) as lat, ST_X(t1.geometry) as lon
    from saplings as t1 
    where sapling_id = {req.sapling_id} and tenant_id={tenant}
     """
    existingD = dbconnect.makeQuery(s1, output='oneJson')
    if not existingD:
        raise HTTPException(status_code=400, detail="Invalid sapling_id")

    # fetch valid species
    s2 = f""" select species_id from species where tenant_id = {tenant} """
    existingSpecies = dbconnect.makeQuery(s2, output="column")
    print(f"existingSpecies: {existingSpecies}")

    uHolder = []
    if req.name and req.name != existingD['name']: 
        uHolder.append(f"name = '{req.name}'")
    # if req.local_name and req.local_name != existingD['local_name']: 
    #     uHolder.append(f"local_name = '{req.local_name}'")
    # if req.botanical_name and req.botanical_name != existingD['botanical_name']: 
    #     uHolder.append(f"botanical_name = '{req.botanical_name}'")

    if req.species_id and req.species_id != existingD['species_id']:     
        if req.species_id not in existingSpecies:
            raise HTTPException(status_code=400, detail="Invalid species_id")
        uHolder.append(f"species_id = {req.species_id}")

    if req.planted_date and req.planted_date != existingD['planted_date'].strftime('%Y-%m-%d'): 
        uHolder.append(f"planted_date = '{req.planted_date}'")
    if req.data_collection_date and req.data_collection_date != existingD['data_collection_date'].strftime('%Y-%m-%d'): 
        uHolder.append(f"data_collection_date = '{req.data_collection_date}'")
    
    if req.descr and req.descr != existingD['descr']: 
        uHolder.append(f"descr = '{req.descr}'")

    if req.height and req.height != existingD['height']: 
        uHolder.append(f"height = {req.height}")
    if req.canopy and req.canopy != existingD['canopy']: 
        uHolder.append(f"canopy = {req.canopy}")
    if req.girth_1m and req.girth_1m != existingD['girth_1m']: 
        uHolder.append(f"girth_1m = {req.girth_1m}")

    if req.lat and req.lon and cf.checkLLchange(req.lat, req.lon, existingD['lat'], existingD['lon'] ):
        uHolder.append(f"geometry = ST_GeomFromText('POINT({req.lon} {req.lat})', 4326 )")

    if not len(uHolder):
        raise HTTPException(status_code=400, detail="Nothing to update")
    
    uHolder.append(f"modified_on = CURRENT_TIMESTAMP")
    uHolder.append(f"modified_by = {user_id}")

    u1 = f"""update saplings
    set {','.join(uHolder)}
    where sapling_id = '{req.sapling_id}'
    and tenant_id = {tenant}
    """
    u1Count = dbconnect.execSQL(u1)

    if u1Count == 1:
        returnD = {'status': 'success', 'sapling_id': req.sapling_id}
        return returnD
    else:
        raise HTTPException(status_code=500, detail="Not able to update in DB")


########################


# smaller api call to get all confirmed saplings' id and name only for dropdown in Observations page
@app.get("/API/getSaplingsList", tags=["saplings"])
def getSaplingsList(withObs: Optional[str] = 'N', x_access_key: Optional[str] = Header(None)):
    cf.logmessage("getSaplingsList api call")
    
    tenant, user_id, role = authenticate(x_access_key, allowed_roles=['admin','moderator','saplings_admin','saplings_entry'])

    returnD = {'status':'success'}

    s1 = f"""select t1.sapling_id, t1.name as sapling_name
    from saplings as t1
    where t1.confirmed = TRUE
    order by t1.name
    """
    df1 = dbconnect.makeQuery(s1, output='df')

    # in case withObs = Y
    cf.logmessage(f"withObs: {withObs}")
    if withObs.upper() == 'Y':
        s2 = f"""select distinct sapling_id from observations"""
        obs_saplings = dbconnect.makeQuery(s2, output='column')
        # now filter df1 by these values
        df1 = df1[df1['sapling_id'].isin(obs_saplings)].copy()

    returnD['saplings'] = df1.to_dict(orient='records')
    return returnD



########################

# another smaller api call to get saplings data for display in saplings upload form

@app.get("/API/saplingsPreview", tags=["saplings"])
def saplingsPreview():
    cf.logmessage("saplingsPreview api call")

    returnD = {'status':'success'}

    # cols = """id, lat, lon, name, planted_date,
    # `group`, `status`, confirmed, first_photos, 
    # local_name, botanical_name"""
    cols = """sapling_id, name, planted_date, ST_Y(geometry) as lat, ST_X(geometry) as lon"""
    
    s1 = f"""select {cols} from saplings"""
    returnD['data'] = dbconnect.makeQuery(s1, output='list')

    # make into csv for min payload size
    return returnD

