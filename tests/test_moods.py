import urllib.request
import json

def test_mood(mood, prompt=''):
    payload = json.dumps({'mood': mood, 'prompt': prompt, 'max_runtime': 140, 'novelty': 0.6}).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:8000/v1/find-my-watch', data=payload, headers={'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read().decode())
    hero = res['hero']['content']
    print(f"Mood [{mood.upper()}]: Hero is \"{hero['title']}\" ({hero['genres'][:2]}) [Trailer: {hero['trailer_key'] or 'None'}]")

test_mood('comforting', 'I want something funny and cozy for the evening')
test_mood('exciting', 'High adrenaline action movie')
test_mood('reflective', 'Mind bending philosophical sci-fi')
test_mood('mystery', 'Detective murder mystery puzzle')
test_mood('emotional', 'Heartbreaking beautiful drama')
