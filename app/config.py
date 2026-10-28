from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
    bot_token: str = Field(default='', alias='BOT_TOKEN')
    admin_ids_raw: str = Field(default='', alias='ADMIN_IDS')
    database_url: str = Field(default='sqlite+aiosqlite:///./cshop.db', alias='DATABASE_URL')
    bot_username: str = Field(default='', alias='BOT_USERNAME')
    support_username: str = Field(default='Cshopsup', alias='SUPPORT_USERNAME')
    payment_card_number: str = Field(default='621986145781155', alias='PAYMENT_CARD_NUMBER')
    payment_cardholder: str = Field(default='', alias='PAYMENT_CARDHOLDER')
    min_stars_quantity: int = Field(default=50, alias='MIN_STARS_QUANTITY', ge=1)
    referral_reward_stars: int = Field(default=5, alias='REFERRAL_REWARD_STARS', ge=1)
    log_level: str = Field(default='INFO', alias='LOG_LEVEL')

    @property
    def admin_ids(self) -> set[int]:
        result: set[int] = set()
        for item in self.admin_ids_raw.split(','):
            item = item.strip()
            if item.isdigit():
                result.add(int(item))
        return result

@lru_cache
def get_settings() -> Settings:
    return Settings()
