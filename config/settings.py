"""配置管理模块 - 使用 pydantic-settings 从 .env 加载配置"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """基金分析系统全局配置"""

    # === 基金列表 ===
    fund_codes: str = Field(default="", description="逗号分隔的基金代码")

    # === LLM 主模型 ===
    llm_primary_model: str = Field(default="gpt-4o-mini")
    llm_primary_api_key: str = Field(default="")
    llm_primary_base_url: str = Field(default="")

    # === LLM 备选模型 ===
    llm_fallback_model: str = Field(default="deepseek-chat")
    llm_fallback_api_key: str = Field(default="")
    llm_fallback_base_url: str = Field(default="")

    # === LLM 参数 ===
    llm_max_tokens: int = Field(default=2000)
    llm_temperature: float = Field(default=0.3)

    # === 通知渠道 ===
    notify_enabled: bool = Field(default=True)
    wechat_webhook_url: str = Field(default="")
    feishu_webhook_url: str = Field(default="")
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")
    email_smtp_host: str = Field(default="smtp.qq.com")
    email_smtp_port: int = Field(default=465)
    email_sender: str = Field(default="")
    email_password: str = Field(default="")
    email_receivers: str = Field(default="")

    # === 分析参数 ===
    risk_free_rate: float = Field(default=0.025, description="无风险利率")
    nav_history_days: int = Field(default=365, description="净值历史天数")

    # === 存储 ===
    database_url: str = Field(default="sqlite:///data/fund_analysis.db")

    model_config = {"env_file": ".env", "env_prefix": "DFA_"}

    def get_fund_code_list(self) -> list[str]:
        """解析基金代码列表"""
        return [c.strip() for c in self.fund_codes.split(",") if c.strip()]

    def get_email_receiver_list(self) -> list[str]:
        """解析邮件接收者列表"""
        return [r.strip() for r in self.email_receivers.split(",") if r.strip()]
