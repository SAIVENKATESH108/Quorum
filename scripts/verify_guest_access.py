import http.cookiejar
import json
import sys
import urllib.parse
import urllib.request

BASE = 'http://localhost:3005'

def test_unauthenticated_routes():
    print('=== 1. Testing Genuinely Unauthenticated (Incognito) Access ===')
    routes = [
        ('/', 'Landing Page'),
        ('/sign-in', 'Sign In Page'),
        ('/projects', 'Projects Workspace'),
        ('/reports', 'Reports Directory'),
        ('/sources', 'Evidence Sources'),
        ('/agents', 'Agent Mesh Telemetry'),
        ('/settings', 'Workspace Settings'),
    ]
    
    class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirectHandler)

    for path, name in routes:
        req = urllib.request.Request(f'{BASE}{path}', headers={'User-Agent': 'IncognitoJudge/1.0'})
        try:
            resp = opener.open(req)
            content = resp.read().decode('utf-8')
            print(f'  [PASS] {name} ({path}): HTTP {resp.status} - Content length {len(content)}')
            if path == '/sign-in':
                assert 'Hackathon Judge Quick-Access' in content, 'Missing Hackathon Judge Quick-Access text'
                assert 'Enter as Guest Judge' in content, 'Missing Enter as Guest Judge button'
                print('         -> Verified "Hackathon Judge Quick-Access" and "Enter as Guest Judge" present in HTML!')
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                location = e.headers.get('Location')
                print(f'  [FAIL] {name} ({path}): Unexpected redirect {e.code} -> {location}')
                sys.exit(1)
            else:
                print(f'  [FAIL] {name} ({path}): HTTP Error {e.code}')
                sys.exit(1)

def test_guest_judge_flow():
    print('\n=== 2. Testing Guest Judge Quick-Access Flow ===')
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    # POST to /api/auth/guest
    req = urllib.request.Request(
        f'{BASE}/api/auth/guest',
        data=b'{}',
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
    )
    resp = opener.open(req)
    data = json.loads(resp.read().decode('utf-8'))
    print(f'  [PASS] /api/auth/guest responded: {resp.status}')
    print(f'         User: {data.get("user")}')
    print(f'         Redirect: {data.get("redirect")}')
    
    cookies = {c.name: c.value for c in cj}
    print(f'         Cookies set: {list(cookies.keys())}')
    assert 'quorum_session' in cookies, 'quorum_session cookie missing!'
    assert 'quorum_guest_session' in cookies, 'quorum_guest_session cookie missing!'

    # Verify /api/auth/me returns guest user
    req_me = urllib.request.Request(f'{BASE}/api/auth/me')
    resp_me = opener.open(req_me)
    user_me = json.loads(resp_me.read().decode('utf-8'))
    print(f'  [PASS] /api/auth/me returned user: {user_me}')
    assert user_me.get('email') == 'judge@quorum.ai', f'Expected judge@quorum.ai, got {user_me.get("email")}'

    # Verify access to /api/projects
    req_proj = urllib.request.Request(f'{BASE}/api/projects')
    resp_proj = opener.open(req_proj)
    projects = json.loads(resp_proj.read().decode('utf-8'))
    print(f'  [PASS] /api/projects returned {len(projects)} projects for guest session.')

    # Test logout
    req_logout = urllib.request.Request(f'{BASE}/api/auth/logout', data=b'{}', headers={'Content-Type': 'application/json'})
    resp_logout = opener.open(req_logout)
    print(f'  [PASS] /api/auth/logout responded: {resp_logout.status}')

if __name__ == '__main__':
    test_unauthenticated_routes()
    test_guest_judge_flow()
    print('\nALL VERIFICATIONS PASSED!')
