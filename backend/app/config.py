from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "Comunidade Unidos em Cristo API"
    frontend_origin: str = "http://localhost:5500"
    pagseguro_api_base_url: str = "https://sandbox.api.pagseguro.com"
    pagseguro_token: str = ""
    brevo_api_key: str = ""
    email_from: str = "contato@seudominio.com.br"
    database_url: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
