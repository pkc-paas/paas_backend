# api_saplings.py

from typing import Optional
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi import HTTPException, Header
import secrets

from paas_launch import app
import commonfuncs as cf
import dbconnect


class saplingReq(BaseModel):
    criteria: Optional[str] = None

@app.post("/getSaplings")
def getSaplings(r: saplingReq, x_access_key: Optional[str] = Header(None)):
    cf.logmessage(x_access_key)
    s1 = f"select username, role from users where token='{x_access_key}'"
    user = dbconnect.makeQuery(s1, output='oneJson')
    if not user:
        cf.logmessage(f"rejected")
        raise HTTPException(status_code=400, detail="Invalid login")

    s2 = f"select * from saplings"
    df = dbconnect.makeQuery(s2, output='df')
    if not len(df):
        cf.logmessage(f"no data")
        raise HTTPException(status_code=400, detail="No data sorry")
    
    # split it
    df_confirmed = df[df['confirmed']==1]
    df_unconfirmed = df[df['confirmed']!=1]

    returnD = {
        "message" : f"Retrieved {len(df)} saplings",
        "data_confirmed" : df_confirmed.to_dict(orient='records'),
        "data_unconfirmed" : df_unconfirmed.to_dict(orient='records')
    }
    return returnD


@app.get("/getPhoto")
def getPhoto(f: str):
    if os.path.isfile(os.path.join(root, 'photos', f)):
        return FileResponse(os.path.join(root, 'photos', f))
    else:
        print(f"{f} not found")
        return {
            "status" : "FAIL",
            "message" : "not found"
        }