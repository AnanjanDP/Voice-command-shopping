import os
from dotenv import load_dotenv
from jose import jwt
from datetime import datetime, timedelta, timezone

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

if not SECRET_KEY:
    print("SECRET_KEY is not loaded")
    exit()

try:
    token = jwt.encode(
        {
            "sub": "test_user",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    print("JWT created successfully")

    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM]
    )

    print("JWT verified successfully")
    print("User:", payload["sub"])
    print("SECRET_KEY is working correctly!")

except Exception as e:
    print("JWT test failed:", str(e))