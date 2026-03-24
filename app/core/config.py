import os


class Settings:
    app_name = os.getenv("APP_NAME", "UM Tech ServiceLayer")
    environment = os.getenv("ENVIRONMENT", "development")


settings = Settings()
