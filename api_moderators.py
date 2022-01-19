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

    username, role = authenticate(x_access_key, allowed_roles=['admin','moderator'])
    
    returnD = {
        'message': 'success',
        'requested': [],
        'approved': [],
        'rejected': [],
        'saplings': []
    }

    s2 = f"""select t1.*, t2.name, t2.lat, t2.lon, t2.first_photos
    from adoptions as t1
    left join saplings as t2
    on t1.sapling_id = t2.id
    order by t1.created_on
    """
    df1 = dbconnect.makeQuery(s2, output='df')
    if not len(df1):
        return returnD
    # grouping
    df_requested = df1[df1['status']=='requested']
    df_approved = df1[df1['status']=='approved']
    df_rejected = df1[df1['status']=='rejected']
    
    returnD['requested'] = df_requested.to_dict(orient='records')
    returnD['approved'] = df_approved.to_dict(orient='records')
    returnD['rejected'] = df_rejected.to_dict(orient='records')
    
    # saplings - unique'd
    def grouper1(x):
        result = {}
        statuses = x['status'].unique().tolist()
        if 'approved' in statuses:
            result['status'] = 'approved'
        elif 'requested' in statuses:
            result['status'] = 'requested'
        else:
            result['status'] = 'other'
        result['num_requests'] = len(x[x['status']=='requested'])
        return pd.Series(result)

    saplingCols = ['sapling_id','name','lat','lon','first_photos']
    df2 = df1[saplingCols + ['status']].groupby(saplingCols).apply(grouper1).reset_index(drop=False)
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
    
    username, role = authenticate(x_access_key, allowed_roles=['admin','moderator'])
    
    if not len(req.idsList):
        raise HTTPException(status_code=400, detail="No inputs")
    
    timestamp = cf.getTime()
    date1 = cf.getDate()

    # fetch adoption entries as per idsList
    idsListSQL = cf.quoteNcomma(req.idsList)
    s1 = f"""select t1.*, t2.name 
    from adoptions as t1
    left join saplings as t2
    on t1.sapling_id = t2.id
    where t1.id in ({idsListSQL})
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
        set status = 'approved',
        approval_date = '{date1}',
        modified_on = '{timestamp}'
        where id in ({idsListSQL})
        and status = 'requested'
        """
        u1Count = dbconnect.execSQL(u1)

        returnD = { 'status':'success', 'num_approved': u1Count }
        return returnD

    elif req.action.lower() == 'reject':
        # u2 = f"""update adoptions
        # set status = 'rejected',
        # modified_on = '{timestamp}'
        # where id in ({idsListSQL})
        # and status = 'requested'
        # """
        u2 = f"""delete from adoptions
        where id in ({idsListSQL})
        and status = 'requested'
        """
        u2Count = dbconnect.execSQL(u2)

        returnD = { 'status':'success', 'num_rejected': u2Count }
        return returnD
    
    # handle removal of adoption status also
    elif req.action.lower() == 'remove':
        u3 = f"""update adoptions
        set status = 'requested',
        modified_on = '{timestamp}'
        where id in ({idsListSQL})
        and status = 'approved'
        """
        u3Count = dbconnect.execSQL(u3)

        returnD = { 'status':'success', 'num_removed': u3Count }
        return returnD


    else:
        returnD = { 'status':'unknown action' }
        return returnD


###############

