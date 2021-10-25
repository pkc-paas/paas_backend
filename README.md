# Payanam

## Setup
```
pip install fastapi uvicorn[standard]
```

## Run
```
uvicorn paas_launch:app --port 5400 --reload
```

Will start application on port 5400, http://localhost:5400/

In server, to run in background:
```
nohup ./paas_server_launch.sh &
```



--root-path : needed to make the proxy setup work for swagger doc (https://server.nikhilvj.co.in/paas_backend/docs)


### Swagger/OpenAPI docs

http://localhost:8000/docs

