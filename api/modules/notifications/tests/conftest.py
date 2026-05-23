# Python
import os

# Ensure env vars exist before importing modules that read them.
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB_NAME", "soptest_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-do-not-use-in-prod")
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("NOTIFICATIONS_ENABLED", "true")
os.environ.setdefault("NOTIFICATIONS_PROVIDER", "log")
os.environ.setdefault("PHONE_DEFAULT_REGION", "CO")
