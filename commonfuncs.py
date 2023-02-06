#commonfuncs.py
import json, os, time, datetime, uuid, secrets
import pandas as pd

root = os.path.dirname(__file__)
print(root)
timeOffset = 5.5
maxThreads = 8

root = os.path.dirname(__file__)
folders = {
    'sapling_files': os.path.join(root, 'persistent_data', 'sapling_files'),
    'sapling_thumbs': os.path.join(root, 'persistent_data', 'sapling_thumbs'),
    'observation_files': os.path.join(root, 'persistent_data', 'observation_files'),
    'observation_thumbs': os.path.join(root, 'persistent_data', 'observation_thumbs'),
    'uploads': os.path.join(root, 'persistent_data', 'uploads'),
    'logs': os.path.join(root, 'persistent_data','logs')
}


def logmessage( *content ):
    global timeOffset
    timestamp = '{:%Y-%m-%d %H:%M:%S} :'.format(datetime.datetime.utcnow() + datetime.timedelta(hours=timeOffset)) # from https://stackoverflow.com/a/26455617/4355695
    line = ' '.join(str(x) for x in list(content)) # from https://stackoverflow.com/a/3590168/4355695
    print(line) # print to screen also
    filename = 'log.txt'
    if root.startswith('/mnt/'):
        filename = 'local_log.txt'
    with open(os.path.join(folders['logs'],filename), 'a') as f:
        print(timestamp, line, file=f) # file=f argument at end writes to file. from https://stackoverflow.com/a/2918367/4355695

def makeError(message):
    logmessage(message)
    return 400, json.dumps({"status":"error","message":message}, default=str)

def makeSuccess(returnD={}):
    returnD['status'] = 'success'
    return 200, json.dumps(returnD, default=str)


def makeTimeString(x, offset=5.5, format="all"):
    '''
    format values: all, time, date
    '''
    # print(type(x))
    if isinstance(x, pd._libs.tslibs.nattype.NaTType) : return ''
    
    if isinstance(x, (pd._libs.tslibs.timestamps.Timestamp,datetime.datetime, datetime.date) ):
        if format == 'time':
            return (x + datetime.timedelta(hours=offset)).strftime('%H:%M:%S')
        elif format == 'date':
            return (x + datetime.timedelta(hours=offset)).strftime('%Y-%m-%d')
        else:
            # default: all
            return (x + datetime.timedelta(hours=offset)).strftime('%Y-%m-%d %H:%M')
    else:
        return ''


def quoteNcomma(a):
    # turn array into sql IN query string: 'a','b','c'
    holder = []
    for n in a:
        holder.append("'{}'".format(n))
    return ','.join(holder)

def justComma(a):
    return ','.join([str(x) for x in a])

def keyedJson(df, key='trainNo'):
    arr = df.to_dict(orient='records')
    keysList = sorted(df[key].unique().tolist())
    returnD = {}
    for keyVal in keysList:
        returnD[keyVal] = df[df[key]==keyVal].to_dict(orient='records')
    return returnD
    

def IRdateConvert(x):
    # sample: "26 Feb 2021", "4 Mar 2021", "-"
    if x == '-': return None
    x2 = datetime.datetime.strptime(x, '%d %b %Y').strftime('%Y-%m-%d')
    return x2


def parseParams(url):
    # from https://stackoverflow.com/a/5075477/4355695
    parsed = urlparse.urlparse(url)
    return parse_qs(parsed.query)


# def makeUID(nobreaks=False):
#     if nobreaks:
#         return uuid.uuid4().hex
#     else:
#         return str(uuid.uuid4())

def makeUID(length=4):
    while True:
        a = secrets.token_urlsafe(length).upper()
        if a[0].isalpha(): break
    return a


def getDate(timeOffset=5.5, daysOffset=0, returnObj=False):
    d = datetime.datetime.utcnow().replace(microsecond=0) + datetime.timedelta(hours=timeOffset) + datetime.timedelta(days=daysOffset)
    if returnObj: return d
    return d.strftime('%Y-%m-%d')

def getTime(timeOffset=5.5, secsOffset=0, returnObj=False):
    d = datetime.datetime.utcnow().replace(microsecond=0) + datetime.timedelta(hours=timeOffset) + datetime.timedelta(seconds=secsOffset)
    if returnObj: return d
    return d.strftime('%Y-%m-%d %H:%M:%S')

def valiDate(d):
    try:
        datetime.datetime.strptime(d,'%Y-%m-%d')
    except ValueError as e:
        return False
    return True

def validateLL(lat, lon):
    if not isinstance(lat, (int, float)): return False
    if not isinstance(lon, (int, float)): return False

    latLimits = (-90,90)
    lonLimits = (-180,180)

    if lat < latLimits[0] or lat > latLimits[1]: return False
    if lon < lonLimits[0] or lon > lonLimits[1]: return False
    return True

def arraySQL(arr):
    if not isinstance(arr, list):
        arr = [arr]
    quoted = [f"'{x}'" for x in arr]
    return f"array[{','.join(quoted)}]"

def checkLLchange(lat1, lon1, lat2, lon2):
    # if either of latter lat-lon not existing at all, then directly update
    if (not isinstance(lat2,(int, float))) or (not isinstance(lon2,(int, float))):
        return True
    # will round to 6 decimals, and return true if there's been a change in either lat or lon
    latCheck = (round(lat1,6) != round(lat2,6))
    lonCheck = (round(lon1,6) != round(lon2,6))
    return (latCheck or lonCheck)