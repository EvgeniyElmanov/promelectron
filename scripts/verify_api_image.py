import sys
sys.path.insert(0, '/app')
from server.app.main import app

routes = [r.path for r in app.routes if hasattr(r, 'path')]
print('Routes:', routes)
assert '/api/v1/login' in routes or '/login' in routes, 'Missing login route!'
assert '/api/v1/categories' in routes or '/categories' in routes, 'Missing categories route!'
print('OK: API routes present')
