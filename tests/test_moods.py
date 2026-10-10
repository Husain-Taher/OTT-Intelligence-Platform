import urllib.request
import json

def run_mood_check(mood, prompt=''):
    payload = json.dumps({'mood': mood, 'prompt': prompt, 'max_runtime': 140, 'novelty': 0.6}).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:8000/v1/find-my-watch', data=payload, headers={'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read().decode())
    hero = res['hero']['content']
    print(f"Mood [{mood.upper()}]: Hero is \"{hero['title']}\" ({hero['genres'][:2]}) [Trailer: {hero['trailer_key'] or 'None'}]")

if __name__ == '__main__':
    run_mood_check('comforting', 'I want something funny and cozy for the evening')
    run_mood_check('exciting', 'High adrenaline action movie')
    run_mood_check('reflective', 'Mind bending philosophical sci-fi')
    run_mood_check('mystery', 'Detective murder mystery puzzle')
    run_mood_check('emotional', 'Heartbreaking beautiful drama')


