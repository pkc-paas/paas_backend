from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # https://fastapi.tiangolo.com/tutorial/cors/
from fastapi.middleware.gzip import GZipMiddleware # https://fastapi.tiangolo.com/advanced/middleware/
from fastapi.staticfiles import StaticFiles # static html files deploying

app = FastAPI()

# allow cors - from https://fastapi.tiangolo.com/tutorial/cors/
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# enable gzip compression, from https://fastapi.tiangolo.com/advanced/middleware/
app.add_middleware(GZipMiddleware, minimum_size=1000)

# can add modules having api calls below

# import api_sample

import api_users
import api_saplings
import api_sponsors
import api_moderators
import api_observations


app.mount("/static/sapling_photos", StaticFiles(directory="photos", html = False), name="static")
# https://fastapi.tiangolo.com/tutorial/static-files/
# html=True is needed for defaulting to index.html. From https://stackoverflow.com/a/63805506/4355695
app.mount("/static/sapling_thumbs", StaticFiles(directory="sapling_thumbs", html = False), name="static")

app.mount("/static/observation_files", StaticFiles(directory="observation_files", html = False), name="static")
app.mount("/static/observation_thumbs", StaticFiles(directory="observation_thumbs", html = False), name="static")
