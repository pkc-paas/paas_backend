# api_saplings.py

from typing import Optional
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi import HTTPException, Header
import secrets, os

from paas_launch import app
import commonfuncs as cf
import dbconnect
from api_users import authenticate

root = os.path.dirname(__file__)


####################

class saplingReq(BaseModel):
    criteria: Optional[str] = None

@app.post("/API/getSaplings", tags=["saplings"])
def getSaplings(r: saplingReq, x_access_key: Optional[str] = Header(None)):
    cf.logmessage("getSaplings api call")
    # username, role = authenticate(x_access_key) 

    s1 = f"""select t1.id, t1.lat, t1.lon, t1.name, t1.group, 
    t1.local_name, t1.botanical_name, t1.planted_date, t1.data_collection_date,
    t1.description, t1.first_photos, t1.confirmed,
    t2.adopted_name, t2.status as adoption_status
    from saplings as t1
    left join (select adopted_name, status, sapling_id from adoptions where status in ('approved','requested')) as t2
    on t1.id = t2.sapling_id
    """
    df1 = dbconnect.makeQuery(s1, output='df', fillna=False, printit=True)
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
        "data_confirmed" : df_confirmed.to_dict(orient='records'),
        "data_unconfirmed" : df_unconfirmed.to_dict(orient='records')
    }

    # # fetch adoption status
    # s2 = f"""select sapling_id, username, adopted_name, status from adoptions where status in ('approved','requested')"""
    # df2 = dbconnect.makeQuery(s2, output='df', fillna=False, printit=True)
    # # process this into json indexed by sapling_id, handle  
    return returnD


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