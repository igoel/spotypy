#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import os
import json
import uuid
import time
import mps
from threading import Thread, Lock
from bottle import Bottle, static_file, response, request

application = Bottle()

HISTORY = {}
HISTORY_IDS = []
CURRENT = {}
QUEUE = {}
QUEUE_IDS = []

q_lock = Lock()

def check_q():
    global CURRENT, QUEUE, QUEUE_IDS, HISTORY, HISTORY_IDS, q_lock
    with q_lock:
        if not mps.MPLAYER:
            if QUEUE_IDS and QUEUE:
                _start_song(QUEUE[QUEUE_IDS[0]])
                time.sleep(1)
            return
        print "percent_pos: {}".format(mps.MPLAYER.percent_pos)
        if mps.MPLAYER.percent_pos > 98:
            _stop()
            mps.MPLAYER = None


def _start_song(song_data):
    print "starting song {}".format(song_data)
    result = mps.playsong(song_data)
    if result:
        _play(song_data)
    return result

def _play(song_data):
    global CURRENT, QUEUE, QUEUE_IDS, HISTORY, HISTORY_IDS
    if "uuid" not in song_data:
        song_data["uuid"] = str(uuid.uuid4())
    s_uuid = song_data["uuid"]
    if s_uuid in QUEUE_IDS:
        QUEUE_IDS.remove(s_uuid)
    if s_uuid in QUEUE:
        del QUEUE[s_uuid]

    if CURRENT:
        _add_to_history(CURRENT)
    CURRENT = song_data

def _stop():
    global CURRENT, QUEUE, QUEUE_IDS, HISTORY, HISTORY_IDS
    if CURRENT:
        _add_to_history(CURRENT)
    CURRENT = {}

def _add_to_history(son_data):
    global CURRENT, QUEUE, QUEUE_IDS, HISTORY, HISTORY_IDS
    HISTORY[son_data["uuid"]] = son_data
    HISTORY_IDS.append(CURRENT["uuid"])
    if len(HISTORY_IDS) > 10:
        HISTORY_IDS = HISTORY_IDS[1:]
        HISTORY = {uuid:HISTORY[uuid] for uuid in HISTORY_IDS}

def _add_to_q(song_data):
    global CURRENT, QUEUE, QUEUE_IDS, HISTORY, HISTORY_IDS
    if "uuid" not in song_data:
        song_data["uuid"] = str(uuid.uuid4())
    s_uuid = song_data["uuid"]
    QUEUE[s_uuid] = song_data
    QUEUE_IDS.append(s_uuid)

def _remove_from_q(song_data):
    global CURRENT, QUEUE, QUEUE_IDS, HISTORY, HISTORY_IDS
    s_uuid = song_data["uuid"]
    if s_uuid in QUEUE_IDS:
        QUEUE_IDS.remove(s_uuid)
    if s_uuid in QUEUE:
        del QUEUE[s_uuid]


@application.get('/ping')
def ping_get(db, merchant_id):
    return {'reply': 'pong'}


@application.get('/')
def index():
    return static_file("index.html", root=os.path.join(os.path.abspath("./"), "html"))


@application.get('/<filename>')
def files(filename):
    return static_file(filename, root=os.path.join(os.path.abspath("./"), "html"))


@application.get('/search')
def index():
    params = bottle.request.params
    result = mps.search(params["term"])
    response.content_type = 'application/json'
    return json.dumps(result)


@application.post('/play')
def play_song():
    song_data = json.loads(request.body.read())
    result = _start_song(song_data)
    response.content_type = 'application/json'
    return json.dumps({"result": result})


@application.get('/current')
def current():
    global CURRENT
    response.content_type = 'application/json'
    return json.dumps(CURRENT)


@application.get('/history')
def history():
    global HISTORY, HISTORY_IDS
    response.content_type = 'application/json'
    return json.dumps([HISTORY[uuid] for uuid in HISTORY_IDS])


@application.get('/queue')
def queue():
    global QUEUE, QUEUE_IDS
    response.content_type = 'application/json'
    return json.dumps([QUEUE[uuid] for uuid in QUEUE_IDS])


@application.put('/queue')
def add_queue():
    song_data = json.loads(request.body.read())
    _add_to_q(song_data)
    response.content_type = 'application/json'
    return json.dumps(QUEUE)


@application.get('/play')
def play_song():
    global QUEUE, QUEUE_IDS
    result = mps.pause_pause()
    if not result:
        if QUEUE and QUEUE_IDS:
            _start_song(QUEUE[QUEUE_IDS[0]])
    response.content_type = 'application/json'
    return json.dumps({"result": result})


@application.get('/stop')
def stop():
    result = mps.stop()
    _stop()
    response.content_type = 'application/json'
    return json.dumps({"result": result})


@application.get('/pause')
def pause():
    global QUEUE, QUEUE_IDS
    result = mps.pause_pause()
    if not result:
        if QUEUE and QUEUE_IDS:
            _start_song(QUEUE[QUEUE_IDS[0]])
    response.content_type = 'application/json'
    return json.dumps({"result": result})


@application.get('/next')
def next():
    global QUEUE, QUEUE_IDS
    if QUEUE and QUEUE_IDS:
        _start_song(QUEUE[QUEUE_IDS[0]])

@application.get('/prev')
def prev():
    global HISTORY, HISTORY_IDS
    if HISTORY and HISTORY_IDS:
        _start_song(HISTORY[HISTORY_IDS[-1]])


@application.get('/status')
def status():
    response.content_type = 'application/json'
    if not mps.MPLAYER:
        return json.dumps({})
    return json.dumps(mps.status())


@application.get('/percent')
def percent():
    check_q()
    response.content_type = 'application/json'
    if not mps.MPLAYER:
        return json.dumps({"percent": 0})
    return json.dumps({"percent": mps.MPLAYER.percent_pos})


@application.post('/status')
def set_stats():
    status = json.loads(request.body.read())
    if not mps.MPLAYER:
        return json.dumps({})
    for key, value in status.items():
        setattr(mps.MPLAYER, key, value)
    response.content_type = 'application/json'
    return json.dumps({})



if __name__ == "__main__":
    import bottle
    bottle.run(application, host="0.0.0.0", port="9000", reloader=True)
