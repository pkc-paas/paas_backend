# api_moderators.py

from typing import Optional, List
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi import HTTPException, Header
import secrets
import pandas as pd

from paas_launch import app
import commonfuncs as cf
import dbconnect



###############

@app.post("/viewAdoptionEntries")
def viewAdoptionEntries(x_access_key: Optional[str] = Header(None)):
    cf.logmessage("viewAdoptionEntries api call")
    s1 = f"select username, role from users where token='{x_access_key}'"
    user = dbconnect.makeQuery(s1, output='oneJson')
    if not user:
        cf.logmessage(f"rejected")
        raise HTTPException(status_code=400, detail="Invalid login")

    if user.get('role','') not in  ('moderator','admin'):
        raise HTTPException(status_code=400, detail="Insufficient privileges")

    s2 = f"""selet t1.*,
    from adoptions as t1
    order by t1.created_on
    """
    df1 = dbconnect.makeQuery(s2, output='df')
    # to do: grouping
    returnD = {
        'message': 'success',
        'adoption_entries': df1.to_dict(orient='records')
    }
    return returnD


###############

class processAdoptionRequest_singleReq(BaseModel):
    request_id: str
    decision: str
    
class processAdoptionRequest_payload(BaseModel):
    data: List[processAdoptionRequest_singleReq]


@app.post("/processAdoptionRequest")
def processAdoptionRequest(req: processAdoptionRequest_payload, x_access_key: Optional[str] = Header(None)):
    cf.logmessage("requestAdoption api call")
    s1 = f"select username, role from users where token='{x_access_key}'"
    user = dbconnect.makeQuery(s1, output='oneJson')
    if not user:
        cf.logmessage(f"rejected")
        raise HTTPException(status_code=400, detail="Invalid login")

    if user.get('role','') not in  ('moderator','admin'):
        raise HTTPException(status_code=400, detail="Insufficient privileges")

    if not len(req.data):
        raise HTTPException(status_code=400, detail="No inputs")
    
    timestamp = cf.getTime()
    date1 = cf.getDate()

    for r in data:
        # to do: validate decision
        updateArr = [f"status='{r.decision}'"]
        if r.decision == 'approved':
            updateArr.append(f"approver='{user['username']}'")
            updateArr.append(f"approval_date='{date1}'")

        updateArr.append(f"modified_on='{timestamp}'")
        updateArr.append(f"modified_by='{user['username']}'")

        # TO DO
        u1 = f"""update adoptions
        set {', '.join(updateArr)}
        where id='{r.request_id}'
        """
        status = dbconnect.execSQL(u1)
        if not status:
            raise HTTPException(status_code=400, detail="Could not update adoption entry in DB")
        returnD = {
            'message': f"Processed {len(data)} adoption requests"
        }
