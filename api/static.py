"""Serve the built local demo and preserve SPA routes without swallowing API/asset errors."""
from pathlib import PurePosixPath

from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles


class SPAFiles(StaticFiles):
    async def get_response(self, path, scope):
        normalized = path.replace('\\', '/').lstrip('/')
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if (exc.status_code != 404 or normalized == 'api' or normalized.startswith(('api/', 'assets/'))
                    or PurePosixPath(normalized).suffix):
                raise
            return await super().get_response('index.html', scope)
