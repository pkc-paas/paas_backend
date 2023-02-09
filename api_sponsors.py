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
from api_users import authenticate

##########################

class singleReq(BaseModel):
    sapling_id: int
    adopted_name: Optional[str] = None
    comments: Optional[str] = None

class adoptReq(BaseModel):
    data: List[singleReq]

@app.post("/API/requestAdoption", tags=["adoptions"])
def requestAdoption(r: adoptReq, x_access_key: Optional[str] = Header(None)):
    cf.logmessage("requestAdoption api call")

    # user_id, role = authenticate(
    tenant, user_id, role = authenticate(x_access_key, allowed_roles=['sponsor'])
    
    requested_sapling_ids = set([x.sapling_id for x in r.data])
    cf.logmessage('requested_sapling_ids:', requested_sapling_ids)
    
    saplingIdsSQL = cf.justComma(requested_sapling_ids)
    s1 = f"""select t1.*, t2.adoption_status, t2.user_id
    from saplings as t1
    left join adoptions as t2
    on t1.sapling_id = t2.sapling_id
    where t1.sapling_id in ({saplingIdsSQL})
    """
    df1 = dbconnect.makeQuery(s1, output='df', fillna=True)
    if not len(df1):
        cf.logmessage("No valid saplings found")
        raise HTTPException(status_code=400, detail="Invalid sapling ids")
    
    invalid_saplings = set(requested_sapling_ids) - set(df1['sapling_id'])

    # already adopted saplings
    df_adopted = df1[df1['adopted_status'].str.lower()=='adopted'].copy()
    adopted_saplings = set(df_adopted['sapling_id'])

    # already requested saplings - allow these but note
    df_alreadyRequested = df1[df1['adopted_status'].str.lower()=='requested'].copy()
    alreadyRequested_saplings = set(df_alreadyRequested['sapling_id'])

    # already requested AND by the same user
    # TO DO
    df_alreadyRequested_thisuser = df_alreadyRequested[df_alreadyRequested['user_id']==user_id].copy()
    alreadyRequested_thisuser_saplings = set(df_alreadyRequested_thisuser['saplid_id'])

    # available saplings:
    available_saplings = set(requested_sapling_ids) - invalid_saplings - adopted_saplings - alreadyRequested_thisuser_saplings

    # finally, add available saplings data to adoptions table

    # converting fastapi request data array to pandas dataframe, from https://stackoverflow.com/a/60845064/4355695
    df_requested = pd.DataFrame([t.__dict__ for t in r.data ])
    
    df_eligible = df_requested[df_requested['sapling_id'].isin(available_saplings)].copy()
    # df_eligible['sapling_id'] = df_eligible['sapling_id'].apply(lambda x: cf.makeUID() )
    df_eligible['user_id'] = df_eligible['created_by'] = user_id
    df_eligible['adoption_status'] = 'requested'
    df_eligible['tenant_it'] = tenant

    # df_eligible['application_date'] = cf.getDate()
    # df_eligible['created_on'] = cf.getTime()

    print(df_eligible)
    
    status = dbconnect.addTable(df_eligible, 'adoptions')
    if not status:
        # df_eligible.to_csv('df_eligible_error.csv',index=False)
        raise HTTPException(status_code=500, detail="Could not add data to DB")
    
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
    sponsor_user_id: Optional[int] = None
    observations: Optional[bool] = False

@app.post("/API/mySaplings", tags=["saplings"])
def mySaplings(req: mySaplingsReq , x_access_key: Optional[str] = Header(None)):
    """
    Get all saplings adopted by a user and optionally their observations
    """
    cf.logmessage("mySaplings api call")
    # user_id, role = authenticate(
    tenant, user_id, role = authenticate(x_access_key, allowed_roles=['sponsor','admin','moderator'])

    # print("observations:",req.observations)

    if role == 'sponsor':
        sponsor_user_id = username
    else:
        # constrain which roles allowed to do this
        # if role not in ('moderator','admin'):
        #     raise HTTPException(status_code=400, detail="Insufficient privileges")

        if not req.sponsor_user_id:
            raise HTTPException(status_code=400, detail="Missing sponsor_user_id")
        sponsor_user_id = req.sponsor_user_id

        # cf.logmessage(f"this is not a sponsor")
        # raise HTTPException(status_code=400, detail="Insufficient privileges")

    s2 = f"""select t1.*, 
    ST_Y(t2.geometry) as lat, ST_X(t2.geometry) as lon,
    t2.name, t2.local_name, t2.botanical_name,
    t2.planted_date, t2.details, t2.first_photos
    from adoptions as t1 
    left join saplings as t2
    on t1.sapling_id = t2.sapling_id
    where t1.user_id={sponsor_user_id}
    and t1.adoption_status = 'adopted'
    and t2.confirmed = TRUE
    order by t1.approval_date, t1.adopted_name
    """
    df1 = dbconnect.makeQuery(s2, output='df', fillna=True)

    returnD = {
        "message": "success", 
        "saplings": df1.to_dict(orient='records')
    }
    if not len(df1):
        returnD['message'] = f"This sponsor {user_id} doesn't have any approved adopted saplings yet."
        return returnD

    if req.observations:
        cf.logmessage("Fetching observations also")
        sapling_ids = df1['sapling_id'].unique()
        sapling_ids_SQL = cf.justComma(sapling_ids)
        s3 = f"""select t1.* from observations as t1
        where t1.sapling_id in ({sapling_ids_SQL})
        order by t1.observation_date, t1.sapling_id
        """
        df2 = dbconnect.makeQuery(s3, output='df', fillna=True)
        returnD['observations'] = df2.to_dict(orient='records')

    return returnD