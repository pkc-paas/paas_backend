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

# persistent data folders
from commonfuncs import folders
for f in folders.values():
    os.makedirs(f, exist_ok=True)

# can add modules having api calls below

# import api_sample
import api_users
import api_saplings
import api_sponsors
import api_moderators
import api_observations
import api_email
import api_events
import api_species

###########
# STATIC files, uploads etc

# create static folders if not existing
# root = os.path.dirname(__file__)
# folders = {
#     'sapling_files': os.path.join(root, 'persistent_data', 'sapling_files'),
#     'sapling_thumbs': os.path.join(root, 'persistent_data', 'sapling_thumbs'),
#     'observation_files': os.path.join(root, 'persistent_data', 'observation_files'),
#     'observation_thumbs': os.path.join(root, 'persistent_data', 'observation_thumbs'),
#     'uploads': os.path.join(root, 'persistent_data', 'uploads')
# }


app.mount("/static/sapling_files", StaticFiles(directory=folders['sapling_files'], html = False), name="static")
# https://fastapi.tiangolo.com/tutorial/static-files/
# html=True is needed for defaulting to index.html. From https://stackoverflow.com/a/63805506/4355695
app.mount("/static/sapling_thumbs", StaticFiles(directory=folders['sapling_thumbs'], html = False), name="static")

app.mount("/static/observation_files", StaticFiles(directory=folders['observation_files'], html = False), name="static")
app.mount("/static/observation_thumbs", StaticFiles(directory=folders['observation_thumbs'], html = False), name="static")

app.mount("/static/uploads", StaticFiles(directory=folders['uploads'], html = False), name="static")
