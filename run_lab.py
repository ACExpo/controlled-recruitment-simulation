"""Start the loopback-only portfolio demo with a local reviewer credential."""
import os
import secrets
import uvicorn

if __name__ == "__main__":
    if not os.environ.get("RECRUITMENT_REVIEWER_KEY"):
        os.environ["RECRUITMENT_REVIEWER_KEY"] = secrets.token_urlsafe(32)
        print("Temporary local reviewer key:", os.environ["RECRUITMENT_REVIEWER_KEY"], flush=True)
    uvicorn.run("app:app", host="127.0.0.1", port=8000, access_log=False)
