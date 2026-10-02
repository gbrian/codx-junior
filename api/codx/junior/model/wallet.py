from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid


class SpendingPeriod(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class SpendingLimit(BaseModel):
    period: SpendingPeriod = Field(..., description="Period for this spending limit")
    limit_cxjcoins: float = Field(..., gt=0, description="Max cxjcoins allowed to spend in this period")
    current_spent: float = Field(default=0.0, description="Amount spent in current period")
    period_start: Optional[str] = Field(default=None, description="Start datetime (ISO format) of the current period")

    def _now_str(self) -> str:
        return datetime.utcnow().isoformat()

    def _period_expired(self, now: datetime) -> bool:
        if self.period_start is None:
            return True
        try:
            start = datetime.fromisoformat(self.period_start)
        except ValueError:
            return True
        delta = now - start
        if self.period == SpendingPeriod.daily:
            return delta.days >= 1
        elif self.period == SpendingPeriod.weekly:
            return delta.days >= 7
        elif self.period == SpendingPeriod.monthly:
            return delta.days >= 30
        return False

    def reset_if_expired(self):
        now = datetime.utcnow()
        if self._period_expired(now):
            self.period_start = now.isoformat()
            self.current_spent = 0.0

    def has_budget(self, cost: float) -> bool:
        self.reset_if_expired()
        return (self.current_spent + cost) <= self.limit_cxjcoins

    def consume(self, cost: float):
        self.reset_if_expired()
        self.current_spent += cost

    @property
    def remaining(self) -> float:
        self.reset_if_expired()
        return max(0.0, self.limit_cxjcoins - self.current_spent)


class TokenUsage(BaseModel):
    """Records token usage for a single AI call."""
    input_tokens: int = Field(default=0, description="Number of input/prompt tokens consumed")
    output_tokens: int = Field(default=0, description="Number of output/completion tokens consumed")
    input_cost_cxjcoins: float = Field(default=0.0, description="Cost for input tokens in cxjcoins")
    output_cost_cxjcoins: float = Field(default=0.0, description="Cost for output tokens in cxjcoins")
    total_cost_cxjcoins: float = Field(default=0.0, description="Total cost in cxjcoins")
    provider: Optional[str] = Field(default=None, description="Provider name used")
    model: Optional[str] = Field(default=None, description="Model name used")

    @classmethod
    def calculate(
        cls,
        input_tokens: int,
        output_tokens: int,
        input_price_per_k: float,
        output_price_per_k: float,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> "TokenUsage":
        input_cost = (input_tokens / 1000.0) * input_price_per_k
        output_cost = (output_tokens / 1000.0) * output_price_per_k
        return cls(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost_cxjcoins=input_cost,
            output_cost_cxjcoins=output_cost,
            total_cost_cxjcoins=input_cost + output_cost,
            provider=provider,
            model=model,
        )


class WalletTransaction(BaseModel):
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="ISO format timestamp")
    amount_cxjcoins: float = Field(..., description="Positive = credit, Negative = debit")
    description: str = Field(default="")
    usage: Optional[TokenUsage] = Field(default=None, description="Token usage details if this is an AI charge")
    balance_after: float = Field(default=0.0, description="Wallet balance after this transaction")


class Wallet(BaseModel):
    wallet_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(default="Default Wallet")
    balance_cxjcoins: float = Field(default=0.0, description="Current balance in cxjcoins")
    spending_limits: List[SpendingLimit] = Field(
        default_factory=list,
        description="Optional spending limits per period"
    )
    transactions: List[WalletTransaction] = Field(
        default_factory=list,
        description="Transaction history"
    )
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="ISO format creation time")
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="ISO format last update time")
    enabled: bool = Field(default=True)

    def can_afford(self, cost: float) -> tuple[bool, str]:
        """
        Check if the wallet has sufficient balance and all spending limits allow the cost.
        Returns (True, '') if affordable, (False, reason) otherwise.
        """
        if not self.enabled:
            return False, "Wallet is disabled"
        if self.balance_cxjcoins < cost:
            return False, (
                f"Insufficient balance: {self.balance_cxjcoins:.6f} cxjcoins available, "
                f"{cost:.6f} required"
            )
        for limit in self.spending_limits:
            if not limit.has_budget(cost):
                return False, (
                    f"Spending limit exceeded for {limit.period.value} period "
                    f"(limit: {limit.limit_cxjcoins:.4f}, spent: {limit.current_spent:.4f})"
                )
        return True, ""

    def debit(
        self,
        cost: float,
        usage: Optional[TokenUsage] = None,
        description: str = "",
    ) -> WalletTransaction:
        """Debit cost from wallet balance, update spending limits, and record transaction."""
        for limit in self.spending_limits:
            limit.consume(cost)
        self.balance_cxjcoins -= cost
        self.updated_at = datetime.utcnow().isoformat()
        tx = WalletTransaction(
            amount_cxjcoins=-cost,
            description=description or "AI model usage charge",
            usage=usage,
            balance_after=self.balance_cxjcoins,
        )
        self.transactions.append(tx)
        return tx

    def credit(self, amount: float, description: str = "") -> WalletTransaction:
        """Add cxjcoins to the wallet balance and record the transaction."""
        self.balance_cxjcoins += amount
        self.updated_at = datetime.utcnow().isoformat()
        tx = WalletTransaction(
            amount_cxjcoins=amount,
            description=description or "Credit",
            balance_after=self.balance_cxjcoins,
        )
        self.transactions.append(tx)
        return tx

    def get_limit_summary(self) -> List[dict]:
        return [
            {
                "period": lim.period.value,
                "limit_cxjcoins": lim.limit_cxjcoins,
                "current_spent": lim.current_spent,
                "remaining": lim.remaining,
            }
            for lim in self.spending_limits
        ]