# api_sysadmin.py
# for sys admin functions

from typing import Optional, List
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi import HTTPException, Header

from paas_launch import app
import commonfuncs as cf
import dbconnect
from api_users import authenticate

class sys_dbfunc_payload(BaseModel):
    query: str
    executeFlag: Optional[bool] = False

@app.post("/API/sys/dbfunc", tags=["sysadmin"])
def sys_dbfunc(req: sys_dbfunc_payload, x_access_key: Optional[str] = Header(None), X_Forwarded_For: Optional[str] = Header(None)):
    cf.logmessage("sys_dbfunc api call")

    username, role = authenticate(x_access_key, allowed_roles=['admin'])
    returnD = { }

    if not req.executeFlag:
        df1 = dbconnect.makeQuery(req.query, output='df')
        returnD['rowcount'] = len(df1)
        returnD['response'] = df1.to_csv(index=False)
    
    else:
        rowcount = dbconnect.execSQL(req.query, multiStatements=True)
        returnD['rowcount'] = rowcount
    return returnD

