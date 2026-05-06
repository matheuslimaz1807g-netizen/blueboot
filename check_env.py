import os
from dotenv import load_dotenv

# Load .env files, similar to main.py and bot_runner_vps.py
for f in [".env.local", ".env"]:
    if os.path.exists(f):
        load_dotenv(dotenv_path=f, override=False)

ml_cookies = os.getenv("ML_COOKIES")

print(f"Value of ML_COOKIES from environment: {ml_cookies}")
print(f"Type of ML_COOKIES: {type(ml_cookies)}")
print(f"Length of ML_COOKIES: {len(ml_cookies) if ml_cookies else 0}")

if not ml_cookies:
    print("ML_COOKIES is not set or is empty.")
else:
    print("ML_COOKIES is set.")

print("Checking all environment variables loaded:")
for key, value in os.environ.items():
    if "ML_COOKIES" in key:
        print(f"{key}={value}")