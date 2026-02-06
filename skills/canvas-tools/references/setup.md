# Setup (Local .env)

## 1) Create .env

Create a `.env` file in the working directory where you will run scripts.

```
CANVAS_BASE_URL=https://your-school.instructure.com
CANVAS_API_TOKEN=your_token
```

## 2) Verify (Optional)

Run the smoke test script to confirm the config loads and API access works:

```
python3 skills/canvas-tools/scripts/smoke_test.py
```

## Notes

- Keep `.env` out of version control.
- The skill reads these values via `python-dotenv` when available, or from the environment.
