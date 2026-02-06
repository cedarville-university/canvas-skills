# Auth And Configuration

## .env (Current)

Use these variables in `.env`:

- `CANVAS_BASE_URL` (example: `https://your-school.instructure.com`)
- `CANVAS_API_TOKEN`

Load with `python-dotenv` when available:

```python
from dotenv import load_dotenv
import os

load_dotenv()
base_url = os.environ["CANVAS_BASE_URL"]
token = os.environ["CANVAS_API_TOKEN"]
```

## OAuth (Later)

When switching to OAuth, keep the `canvasapi.Canvas(base_url, token)` usage the same and change only how `token` is obtained.

Minimum OAuth data to store (names are suggestions):

- `CANVAS_OAUTH_CLIENT_ID`
- `CANVAS_OAUTH_CLIENT_SECRET`
- `CANVAS_OAUTH_REDIRECT_URI`

Store and refresh OAuth tokens outside the skill. Provide the access token to `Canvas`.
