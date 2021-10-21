# api_data1
from typing import Optional
from pydantic import BaseModel
from fastapi.responses import FileResponse


from paas_launch import app

import pandas as pd
import sys, os, json, time, datetime

root = os.path.dirname(__file__)
absPath = os.path.realpath(__file__)


class Item1(BaseModel):
    description: Optional[str] = None


@app.post("/getData1")
def getData1(item1: Item1):
    returnD = {
        "status" : "SUCCESS",
        "data" : []
    }
    df = pd.read_csv(os.path.join(root,'data','PAAS_ABB_01.csv'))
    returnD['data'] = df.to_dict(orient='records')

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