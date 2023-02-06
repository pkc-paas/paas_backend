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
from api_users import authenticate



###############

@app.post("/API/viewAdoptionEntries", tags=["adoptions"])
def viewAdoptionEntries(x_access_key: Optional[str] = Header(None)):
    cf.logmessage("viewAdoptionEntries api call")

    # user_id, role = authenticate(
    tenant, user_id, role = authenticate(x_access_key, allowed_roles=['admin','moderator'])
    
    returnD = {
        'message': 'success',
        'requested': [],
        'approved': [],
        'rejected': [],
        'saplings': []
    }

    s2 = f"""select t1.*, t2.name, t2.photos,
    ST_Y(t2.geometry) as lat, ST_X(t2.geometry) as lon
    from adoptions as t1
    left join saplings as t2
    on t1.sapling_id = t2.sapling_id
    where t1.tenant_id = {tenant}
    order by t1.created_on desc
    """
    df1 = dbconnect.makeQuery(s2, output='df')
    if not len(df1):
        return returnD
    # grouping
    df_requested = df1.query('adoption_status == "requested"')
    df_approved =  df1.query('adoption_status == "approved"')
    df_rejected = df1.query('adoption_status == "rejected"')
    
    returnD['requested'] = df_requested.to_dict(orient='records')
    returnD['approved'] = df_approved.to_dict(orient='records')
    returnD['rejected'] = df_rejected.to_dict(orient='records')
    
    # saplings - unique'd
    def grouper1(x):
        result = {}
        statuses = x['adoption_status'].unique().tolist()
        if 'approved' in statuses:
            result['adoption_status'] = 'approved'
        elif 'requested' in statuses:
            result['adoption_status'] = 'requested'
        else:
            result['adoption_status'] = 'other'
        result['num_requests'] = len(x.query('adoption_status == "requested"'))
        return pd.Series(result)

    saplingCols = ['sapling_id','name','lat','lon','photos']
    df2 = df1[saplingCols + ['adoption_status']].groupby(saplingCols).apply(grouper1).reset_index(drop=False)
    # print(df2)

    returnD['saplings'] = df2.to_dict(orient='records')

    return returnD


###############

# class processAdoptionRequest_singleReq(BaseModel):
#     request_id: str
#     decision: str
    
class processAdoptionRequest_payload(BaseModel):
    idsList: List[str]
    action: str


@app.post("/API/processAdoptionRequest", tags=["adoptions"])
def processAdoptionRequest(req: processAdoptionRequest_payload, x_access_key: Optional[str] = Header(None)):
    cf.logmessage("processAdoptionRequest api call")
    
    # user_id, role = authenticate(
    tenant, user_id, role = authenticate(x_access_key, allowed_roles=['admin','moderator'])
    
    if not len(req.idsList):
        raise HTTPException(status_code=400, detail="No inputs")
    
    # timestamp = cf.getTime()
    # date1 = cf.getDate()

    # fetch adoption entries as per idsList
    idsListSQL = cf.quoteNcomma(req.idsList)
    s1 = f"""select t1.*, t2.name 
    from adoptions as t1
    left join saplings as t2
    on t1.sapling_id = t2.id
    where t1.id in ({idsListSQL})
    and t1.tenant_id = {tenant}
    order by t1.application_date
    """
    df1 = dbconnect.makeQuery(s1, output='df', keepCols=True)

    # check if same sapling requested multiple
    if req.action.lower() == 'approve':
        saplings = df1['sapling_id'].tolist()
        # find dupes in a list. from https://www.iditect.com/guide/python/python_howto_find_the_duplicates_in_a_list.html
        dupes = set([x for x in saplings if saplings.count(x) > 1])

        if len(dupes):
            namesList = []
            dupesSQL = cf.quoteNcomma(dupes)
            for x in dupes:
                df2 = df1[df1['sapling_id'] == x]
                if not len(df2):
                    continue
                name = df2['name'].tolist()[0]
                namesList.append(name)

            returnD = { 'status': 'duplicates', 'dupeIds': namesList }
            return returnD
        
        u1 = f"""update adoptions
        set adoption_status = 'approved',
        approval_date = CURRENT_DATE,
        modified_on = CURRENT_TIMESTAMP
        where id in ({idsListSQL})
        and tenant_id = {tenant}
        and adoption_status = 'requested'
        """
        u1Count = dbconnect.execSQL(u1)

        returnD = { 'status':'success', 'num_approved': u1Count }
        return returnD

    elif req.action.lower() == 'reject':
        u2 = f"""delete from adoptions
        where id in ({idsListSQL})
        and adoption_status = 'requested'
        and tenant_id = {tenant}
        """
        u2Count = dbconnect.execSQL(u2)

        returnD = { 'status':'success', 'num_rejected': u2Count }
        return returnD
    
    # handle revert of adoption status back to requested also
    elif req.action.lower() == 'remove':
        u3 = f"""update adoptions
        set adoption_status = 'requested',
        modified_on = CURRENT_TIMESTAMP,
        approval_date = NULL
        where id in ({idsListSQL})
        and adoption_status = 'approved'
        and tenant_id = {tenant}
        """
        u3Count = dbconnect.execSQL(u3)

        returnD = { 'status':'success', 'num_removed': u3Count }
        return returnD


    else:
        returnD = { 'status':'unknown action' }
        return returnD


###############

