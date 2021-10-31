# api_sponsors.py

from typing import Optional, List
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi import HTTPException, Header
import secrets
import pandas as pd

from paas_launch import app
import commonfuncs as cf
import dbconnect


##########################

class singleReq(BaseModel):
    sapling_id: str
    adopted_name: Optional[str] = None
    comments: Optional[str] = None

class adoptReq(BaseModel):
    data: List[singleReq]

@app.post("/requestAdoption")
def requestAdoption(r: adoptReq, x_access_key: Optional[str] = Header(None)):
    cf.logmessage("requestAdoption api call")
    s1 = f"select username, role from users where token='{x_access_key}'"
    user = dbconnect.makeQuery(s1, output='oneJson')
    if not user:
        cf.logmessage(f"rejected")
        raise HTTPException(status_code=400, detail="Invalid login")

    if user.get('role','') != 'sponsor':
        cf.logmessage(f"this is not a sponsor")
        raise HTTPException(status_code=400, detail="Insufficient privileges")
    
    requested_sapling_ids = set([x.sapling_id for x in r.data])
    cf.logmessage('requested_sapling_ids:', requested_sapling_ids)
    
    saplingIdsSQL = cf.quoteNcomma(requested_sapling_ids)
    s1 = f"""select t1.*, t2.status as adopted_status, t2.username
    from saplings as t1
    left join adoptions as t2
    on t1.id = t2.sapling_id
    where t1.id in ({saplingIdsSQL})
    """
    df1 = dbconnect.makeQuery(s1, output='df', fillna=True)
    if not len(df1):
        cf.logmessage("No valid saplings found")
        raise HTTPException(status_code=400, detail="Invalid sapling ids")
    
    invalid_saplings = set(requested_sapling_ids) - set(df1['id'])

    # already adopted saplings
    df_adopted = df1[df1['adopted_status'].str.lower()=='adopted'].copy()
    adopted_saplings = set(df_adopted['id'])

    # already requested saplings - allow these but note
    df_alreadyRequested = df1[df1['adopted_status'].str.lower()=='requested'].copy()
    alreadyRequested_saplings = set(df_alreadyRequested['id'])

    # already requested AND by the same user
    # TO DO
    df_alreadyRequested_thisuser = df_alreadyRequested[df_alreadyRequested['username']==user['username']].copy()
    alreadyRequested_thisuser_saplings = set(df_alreadyRequested_thisuser['id'])

    # available saplings:
    available_saplings = set(requested_sapling_ids) - invalid_saplings - adopted_saplings - alreadyRequested_thisuser_saplings

    # finally, add available saplings data to adoptions table

    # converting fastapi request data array to pandas dataframe, from https://stackoverflow.com/a/60845064/4355695
    df_requested = pd.DataFrame([t.__dict__ for t in r.data ])
    
    df_eligible = df_requested[df_requested['sapling_id'].isin(available_saplings)].copy()

    print("Eligible:", )
    df_eligible['id'] = df_eligible['sapling_id'].apply(lambda x: cf.makeUID() )
    df_eligible['username'] = df_eligible['created_by'] = user['username']
    df_eligible['status'] = 'requested'
    df_eligible['application_date'] = cf.getDate()
    df_eligible['created_on'] = cf.getTime()

    
    status = dbconnect.addTable(df_eligible, 'adoptions')
    if not status:
        df_eligible.to_csv('df_eligible_error.csv',index=False)
        raise HTTPException(status_code=400, detail="Could not add data to DB")
    
    returnD = {
        "message": "success", 
        "requested": df_eligible['sapling_id'].tolist(),
        "invalid": list(invalid_saplings),
        "already_adopted": list(adopted_saplings),
        "requested_by_others_also": list(alreadyRequested_saplings),
        "already_requested": list(alreadyRequested_thisuser_saplings)
    }
    return returnD


##############################

class mySaplingsReq(BaseModel):
    sponsor_username: Optional[str] = None
    observations: Optional[bool] = False

@app.post("/mySaplings")
def mySaplings(req: mySaplingsReq , x_access_key: Optional[str] = Header(None)):
    """
    Get all saplings adopted by a user and optionally their observations
    """
    cf.logmessage("mySaplings api call")
    s1 = f"select username, role from users where token='{x_access_key}'"
    user = dbconnect.makeQuery(s1, output='oneJson')
    if not user:
        cf.logmessage(f"rejected")
        raise HTTPException(status_code=400, detail="Invalid login")

    cf.logmessage(f"user: {user['username']}, role: {user['role']}")
    print("observations:",req.observations)

    if user.get('role','') == 'sponsor':
        sponsor_username = user.get('username')
    else:
        # constrain which roles allowed to do this
        if user.get('role','') not in ('moderator','admin'):
            raise HTTPException(status_code=400, detail="Insufficient privileges")

        if not req.sponsor_username:
            raise HTTPException(status_code=400, detail="Missing sponsor_username")
        sponsor_username = req.sponsor_username

        # cf.logmessage(f"this is not a sponsor")
        # raise HTTPException(status_code=400, detail="Insufficient privileges")

    s2 = f"""select t1.*, 
    t2.lat, t2.lon, t2.name, t2.`group`, t2.local_name, t2.botanical_name,
    t2.planted_date, t2.details, t2.first_photos
    from adoptions as t1 
    left join saplings as t2
    on t1.sapling_id = t2.id
    where t1.username='{sponsor_username}'
    and t1.status = 'adopted'
    and t2.confirmed = 1
    order by t1.approval_date, t1.adopted_name
    """
    df1 = dbconnect.makeQuery(s2, output='df', fillna=True)

    returnD = {
        "message": "success", 
        "saplings": df1.to_dict(orient='records')
    }
    if not len(df1):
        returnD['message'] = f"This sponsor {user['username']} doesn't have any approved adopted saplings yet."
        return returnD

    if req.observations:
        sapling_ids = df1['sapling_id'].unique()
        sapling_ids_SQL = cf.quoteNcomma(sapling_ids)
        s3 = f"""select t1.* from observations as t1
        where t1.sapling_id in ({sapling_ids_SQL})
        order by t1.observation_date, t1.id
        """
        df2 = dbconnect.makeQuery(s3, output='df', fillna=True)
        returnD['observations'] = df2.to_dict(orient='records')

    return returnD