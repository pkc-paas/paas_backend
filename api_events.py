# api_events.py

from typing import Optional, List
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi import HTTPException, Header, File, UploadFile, Form
import secrets
import pandas as pd

from paas_launch import app
import commonfuncs as cf
import dbconnect
from api_users import authenticate


########

class eventsList_payload(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@app.post("/API/eventsList", tags=["events"])
def eventsList(r: eventsList_payload): #, x_access_key: Optional[str] = Header(None)):
    cf.logmessage("eventsList api call")

    if not r.start_date:
        r.start_date = cf.getDate(daysOffset=-5)


    if not r.end_date:
        r.end_date = cf.getDate(daysOffset=60)

    returnD = {}
    
    s1 = f"""select * from events
    where start_date between '{r.start_date}' and '{r.end_date}'
    """
    df1 = dbconnect.makeQuery(s1, output='df')

    # bit columns come as b'\x01' , b'\x00' . python's inbuilt ord() function converts them to 1, 0. 
    # from https://stackoverflow.com/a/34920161/4355695, https://docs.python.org/3.4/library/functions.html#ord
    if len(df1):
        df1['disabled'] = df1['disabled'].apply(ord)
        df1['highlight'] = df1['highlight'].apply(ord)

        del df1['created_by'], df1['created_on'], df1['modified_on'], df1['modified_by']

    returnD['events'] = df1.to_dict(orient='records')
    return returnD


########

# trying a mix of file upload and json payload here

class createEvent_payload(BaseModel):
    title: str
    start_date: str
    end_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    description: Optional[str] = None
    files: Optional[str] = None
    tags: Optional[str] = None
    highlight: Optional[str] = None
    join_link: Optional[str] = None
    location_addr: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

@app.post("/API/createEvent", tags=["events"])
def createEvent(
        r: createEvent_payload, 
        x_access_key: str = Header(...),
        uploadFiles: List[UploadFile] = File(...)
        ):
    cf.logmessage("createEvent api call")

    print(r)
    username, role = authenticate(x_access_key, allowed_roles=['admin'])

    returnD = {}

    # validations
    s1 = f"select count(*) from events where start_date = '{r.start_date}' and title='{r.title}' and disabled=0"
    c1 = dbconnect.makeQuery(s1, output='oneValue')
    if c1:
        raise HTTPException(status_code=400, detail="There is already an event with same title and start date in the system, please edit that.")


    iCols = []
    iVals = []

    iCols.append('title')
    iVals.append(f"'{r.title}'")

    iCols.append('start_date')
    iVals.append(f"'{r.start_date}'")
    
    if r.end_date:
        iCols.append('end_date')
        iVals.append(f"'{end_date}'")

    if r.start_time:
        iCols.append('start_time')
        iVals.append(f"'{start_time}'")
    
    if r.end_time:
        iCols.append('end_time')
        iVals.append(f"'{end_time}'")
    
    if r.end_date:
        iCols.append('description')
        iVals.append(f"'{description}'")
    
    if r.end_date:
        iCols.append('end_date')
        iVals.append(f"'{end_date}'")
    
    if r.description:
        iCols.append('description')
        iVals.append(f"'{description}'")
    
    if r.end_date:
        iCols.append('end_date')
        iVals.append(f"'{end_date}'")
    
    if r.end_date:
        iCols.append('end_date')
        iVals.append(f"'{end_date}'")
    
    if r.end_date:
        iCols.append('end_date')
        iVals.append(f"'{end_date}'")
    
    if r.end_date:
        iCols.append('end_date')
        iVals.append(f"'{end_date}'")
    



    columnsEnd = ''
    if len(iCols): columnsEnd = f", {','.join(iCols)}"
    valuesEnd = ''
    if len(iVals): valuesEnd = f", {','.join(iVals)}"

    i1 = f"""insert into events (evid, title, start_date {columnsEnd})
    values ('{evid}', '{title}', '{start_date}' {valuesEnd})
    """
    i1Count = dbconnect.execSQL(i1, noprint=False)

    returnD = {'status':'success', 'evid':evid}
    return returnD



########

class editEvent_payload(BaseModel):
    event_id: str
    title: str
    start_date: str
    end_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    description: Optional[str] = None
    files: Optional[str] = None
    tags: Optional[str] = None
    highlight: Optional[str] = None
    join_link: Optional[str] = None
    location_addr: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

@app.post("/API/editEvent", tags=["events"])
def editEvent(r: editEvent_payload, x_access_key: Optional[str] = Header(None)):
    cf.logmessage("editEvent api call")