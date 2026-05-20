from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Ozon API credentials
    ozon_client_id: str = Field(..., description="Ozon Seller Client-Id")
    ozon_token_reader: SecretStr = Field(..., description="Ozon Seller API key")
    ozon_base_url: str = Field(
        default="https://api-seller.ozon.ru",
        description="Ozon Seller API base URL",
    )
    ozon_request_timeout: int = Field(
        default=60,
        ge=5,
        le=300,
        description="Total timeout in seconds for a single Ozon API request",
    )

    # ClickHouse connection
    clickhouse_host: str = Field(default="localhost")
    clickhouse_port: int = Field(default=8123)
    clickhouse_user: str = Field(default="default")
    clickhouse_password: SecretStr = Field(default=SecretStr(""))
    clickhouse_database: str = Field(default="default")
    clickhouse_batch_size: int = Field(
        default=5000,
        ge=100,
        le=100000,
        description="Number of rows per ClickHouse INSERT batch",
    )

    # Scheduling (cron expressions)
    products_cron: str = Field(
        default="0 */4 * * *",
        description="Cron expression for products sync (default: every 4 hours)",
    )
    orders_cron: str = Field(
        default="*/30 * * * *",
        description="Cron expression for orders sync (default: every 30 minutes)",
    )
    transactions_cron: str = Field(
        default="0 3 * * *",
        description="Cron expression for transactions sync (default: daily at 03:00)",
    )
    stocks_cron: str = Field(
        default="0 */4 * * *",
        description="Cron expression for stocks snapshot (default: every 4 hours)",
    )
    prices_cron: str = Field(
        default="0 */4 * * *",
        description="Cron expression for prices sync (default: every 4 hours)",
    )
    analytics_cron: str = Field(
        default="0 4 * * *",
        description="Cron expression for analytics sync (default: daily at 04:00)",
    )
    product_queries_cron: str = Field(
        default="0 5 * * *",
        description="Cron expression for product queries sync (default: daily at 05:00)",
    )
    categories_cron: str = Field(
        default="0 2 * * *",
        description="Cron expression for categories sync (default: daily at 02:00)",
    )
    price_timer_interval_days: int = Field(
        default=7,
        ge=1,
        le=90,
        description="Interval in days for price timer update (default: every 7 days)",
    )

    # Logging
    log_level: str = Field(default="INFO")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
