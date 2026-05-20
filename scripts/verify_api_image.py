import sys
sys.path.insert(0, '/app')
from server.app.main import app

routes = [r.path for r in app.routes if hasattr(r, 'path')]
print('Routes:', routes)
assert '/api/v1/login' in routes or '/login' in routes, 'Missing login route!'
assert any('/categories' in r for r in routes), f'Missing categories route! Got: {routes}'
print('OK: API routes present')
