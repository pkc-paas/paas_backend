# # api_data1

# # 2021-10-25 : Keeping for legacy, but using the api in api_saplings now.

# from typing import Optional
# from pydantic import BaseModel
# from fastapi.responses import FileResponse


# from paas_launch import app

# import pandas as pd
# import sys, os, json, time, datetime

# root = os.path.dirname(__file__)
# absPath = os.path.realpath(__file__)


# class Item1(BaseModel):
#     description: Optional[str] = None


# @app.post("/API/getData1")
# def getData1(item1: Item1):
#     returnD = {
#         "status" : "SUCCESS",
#         "data" : []
#     }
#     df = pd.read_csv(os.path.join(root,'data','PAAS_ABB_01.csv'))
#     returnD['data'] = df.to_dict(orient='records')

#     return returnD
