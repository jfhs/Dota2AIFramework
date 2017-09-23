import gym
from gym import spaces
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import subprocess
import time
from threading import Thread
import math

OBSERVATIONS_PER_UNIT = 8
# coords (3) + hp + max hp + armor + damage + isEnemy
OBSERVATIONS_FOR_ME = 7
# coords (3) + hp + mp + damage + isAttacking
DOTA_PATH = 'C:\\Program Files (x86)\\Steam\\steamapps\\common\\dota 2 beta\\game\\bin\\win64\\dota2.exe'
DOTA_DEFAULT_ARGS = ['-console', '-condebug']
TIMESCALE = 10
STEP_UNIT = 100
STARTING_LOC = [-1041, -585, 128]

def json2vec(unit):
    return [unit['origin'][0], unit['origin'][1], unit['origin'][2]]

def dist_key(unit):
    uo = json2vec(unit)

    def keyer(a):
        ao = json2vec(a)
        return (uo[0] - ao[0]) * (uo[0] - ao[0]) + (uo[1] - ao[1]) * (uo[1] - ao[1])
    return keyer


stop_httpd = False

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        global stop_httpd
        #print("Received POST")
        content_len = int(self.headers['Content-Length'])
        post_body = self.rfile.read(content_len)
        last_json = json.loads(post_body)
        #print("RECEIVED REQUEST WITH DATA " + str(post_body))
        d2env = Dota2Env.instance
        d2env._updateObservation(last_json)
        d2env.result = None
        while d2env.result is None:
            time.sleep(0.01)
            if stop_httpd:
                return
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(json.dumps(d2env.result), 'utf-8'))
        # self.finish()

def run_threaded_server():
    print("Starting HTTP server")
    httpd = HTTPServer(('', 8080), Handler)
    httpd.timeout = 0.1
    while not stop_httpd:
        httpd.handle_request()
    print("Stopping HTTP server")
    httpd.socket.close()
    #httpd.shutdown()
    print("HTTP shutdown completed")

class Dota2Env(gym.Env):
    def __init__(self, n_moves=9, n_units=10):
        self.n_units = n_units
        self.n_moves = n_moves
        self.action_space = spaces.Discrete(
            self.n_moves +
            self.n_units +
            1 # for noop
        )
        self.observation_space = spaces.Discrete(
            OBSERVATIONS_FOR_ME +
            self.n_units * OBSERVATIONS_PER_UNIT
        )
        self.dotaprocess = None
        self.thread = None
        Dota2Env.instance = self

    def _run_dota(self):
        if self.dotaprocess:
            self.dotaprocess.kill()
        self.dotaprocess = subprocess.Popen([DOTA_PATH] + DOTA_DEFAULT_ARGS + ['+sv_cheats 1', '+host_timescale ' + str(TIMESCALE), '+dota_launch_custom_game d2ai dota'])

    def _getCreepsKilled(self, world):
        me = self._getMe(world)
        if me is None:
            return 0
        return me['denies'] + me['lasthits']

    def _computeReward(self, prev, cur):
        mePrev = self._getMe(prev)
        meCur = self._getMe(cur)
        if meCur is None or mePrev is None:
            return 0
        curCreeps = self._getCreepsKilled(cur)
        prevCreeps = self._getCreepsKilled(prev)
        curXp = meCur['xp']
        prevXp = mePrev['xp']
        return (curCreeps - prevCreeps) #+ (curXp - prevXp) * 0.001

    def _getMe(self, world = None):
        world = self.last_json if world is None else world
        entities = world['entities']
        myId = str(world['myHeroId'])
        if myId not in entities:
            return None
        return entities[myId]

    def _doAction(self, action):
        res = {
            'command': 'NOOP'
        }
        if action < self.n_moves:
            degrees_per_dir = math.radians(360/self.n_moves)
            me = self._getMe()
            if me is not None:
                myPos = me['origin']
                angle = degrees_per_dir * action
                myPos[0] += math.sin(angle) * STEP_UNIT
                myPos[1] += math.cos(angle) * STEP_UNIT
                res = {
                    'command': 'MOVE',
                    'x': myPos[0],
                    'y': myPos[1],
                    'z': myPos[2],
                }
        elif action < self.n_moves + self.n_units:
            uid = action - self.n_moves
            if uid < len(self.last_units_ids):
                res = {
                    'command': 'ATTACK',
                    'target': self.last_units_ids[uid]
                }
        print("Doing action: " + res['command'])
        self.result = res
        prev_json = self.last_json
        self.waiting = True
        self._waitForObservation()
        return self._computeReward(prev_json, self.last_json)

    def _isDone(self):
        # if self._getMe() is not None:
        #     print("isDone? me is not dead me.alive=" + str(self._getMe()['alive']) + "creeps=" + str(self.lastKnownCreeps))
        # else:
        #     print("isDone? me is dead and creeps=" + str(self.lastKnownCreeps))
        return \
            ((self._getMe() is None or not self._getMe()['alive'])) or \
            self.last_json['gameTime'] > 600
        #and self.lastKnownCreeps > 0) or \
    def _step(self, action):
        assert self.action_space.contains(action)
        print("Got action " + str(action))

        reward = self._doAction(action)
        done = self._isDone()

        return self.last_observation, reward, done, {}

    def _waitForObservation(self):
        print("Asking to handle one request")
        while self.waiting:
            time.sleep(0.01)
        print("Returning")
        return self.last_observation

    def _observationsForMe(self):
        me = self._getMe()
        if me is None:
            return [-1] * OBSERVATIONS_FOR_ME
        return [
            me['origin'][0],
            me['origin'][1],
            me['origin'][2],
            me['health'],
            me['mana'],
            me['damage'],
            1 if me['isAttacking'] else 0
        ]

    def _unitObservations(self, unit):
        me = self._getMe()
        if me is None or unit is None:
            return [-1] * OBSERVATIONS_PER_UNIT
        return [
            unit['origin'][0],
            unit['origin'][1],
            unit['origin'][2],
            unit['health'],
            unit['maxHealth'],
            unit['armor'],
            unit['damage'],
            0 if unit['team'] == me['team'] else 1
        ]

    def isValidTarget(self, target, myId):
        return \
            target['id'] != myId and \
            target['type'] in ["Hero", "BaseNPC"] and \
            target['alive']

    def _unitsObservations(self):
        entities = self.last_json['entities']
        me = self._getMe()
        validTargets = [u for u in entities.values() if self.isValidTarget(u, self.last_json['myHeroId'])]
        if me is None or me['origin'] is None:
            sortedUnits = validTargets
        else:
            sortedUnits = sorted(validTargets, key=dist_key(me))
        self.last_units_ids = [u['id'] for u in sortedUnits]
        result = []
        for i in range(self.n_units):
            result += self._unitObservations(sortedUnits[i] if i < len(sortedUnits) else None)
        return result

    def _updateObservation(self, json):
        self.waiting = False
        self.last_json = json
        self.last_observation = self._observationsForMe() + self._unitsObservations()
        self.lastKnownCreeps = self._getCreepsKilled(self.last_json) if self._getMe() is not None else self.lastKnownCreeps

    def handler(self, request):
        print("Received request")
        post_body = request.body()
        last_json = json.loads(post_body)
        print("RECEIVED REQUEST WITH DATA " + str(post_body))
        self._updateObservation(last_json)

    def _verifyIsNearMiddle(self):
        while True:
            print("Going to center")
            self.waiting = True
            obs = self._waitForObservation()

            if math.fabs(obs[0] - STARTING_LOC[0]) + math.fabs(obs[1] - STARTING_LOC[1]) < 100:
                print("In center! Starting game :D")
                return obs
            self.result = {
                'command': 'MOVE',
                'x': STARTING_LOC[0],
                'y': STARTING_LOC[1],
                'z': STARTING_LOC[2],
            }

    def _reset(self):
        self._run_dota()
        self.waiting = True
        self.lastKnownCreeps = 0
        if self.thread is not None:
            global stop_httpd
            stop_httpd = True
            print("Waiting for httpd to stop")
            self.thread.join()
            print("Httpd stopped")
            stop_httpd = False
        self.thread = Thread(target=run_threaded_server)
        self.thread.start()
        while True:
            print("Going to center")
            self.waiting = True
            obs = self._waitForObservation()

            if math.fabs(obs[0] - STARTING_LOC[0]) + math.fabs(obs[1] - STARTING_LOC[1]) < 100:
                print("In center! Starting game :D")
                return obs
            self.result = {
                'command': 'MOVE',
                'x': STARTING_LOC[0],
                'y': STARTING_LOC[1],
                'z': STARTING_LOC[2],
            }

gym.envs.register(
    id='dota2-v0',
    entry_point='d2env:Dota2Env'
)