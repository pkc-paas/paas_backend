from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # https://fastapi.tiangolo.com/tutorial/cors/
from fastapi.staticfiles import StaticFiles # static html files deploying
from brotli_asgi import BrotliMiddleware # https://github.com/fullonic/brotli-asgi
import os

app = FastAPI()

# allow cors - from https://fastapi.tiangolo.com/tutorial/cors/
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# enable Brotli compression. Better for json payloads, supported by most browsers. Fallback to gzip by default. from https://github.com/fullonic/brotli-asgi
app.add_middleware(BrotliMiddleware)

# can add modules having api calls below

# import api_sample

import api_users
import api_saplings
import api_sponsors
import api_moderators
import api_observations
import api_email
import api_events

###########
# STATIC files, uploads etc

# create static folders if not existing
root = os.path.dirname(__file__)
folders = [
    os.path.join(root, 'persistent_data', 'photos'),
    os.path.join(root, 'persistent_data', 'sapling_thumbs'),
    os.path.join(root, 'persistent_data', 'observation_files'),
    os.path.join(root, 'persistent_data', 'observation_thumbs'),
    os.path.join(root, 'persistent_data', 'uploads')
]
for f in folders:
    os.makedirs(f, exist_ok=True)

app.mount("/static/sapling_photos", StaticFiles(directory="persistent_data/photos", html = False), name="static")
# https://fastapi.tiangolo.com/tutorial/static-files/
# html=True is needed for defaulting to index.html. From https://stackoverflow.com/a/63805506/4355695
app.mount("/static/sapling_thumbs", StaticFiles(directory="persistent_data/sapling_thumbs", html = False), name="static")

app.mount("/static/observation_files", StaticFiles(directory="persistent_data/observation_files", html = False), name="static")
app.mount("/static/observation_thumbs", StaticFiles(directory="persistent_data/observation_thumbs", html = False), name="static")

app.mount("/static/files", StaticFiles(directory="persistent_data/uploads", html = False), name="static")
