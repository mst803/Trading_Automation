from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class SignalEnum(str, Enum):
    """Valid trading signals"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class TradingSignal(BaseModel):
    """Minimal trading signal with required fields only"""
    signal: SignalEnum = Field(..., description="Trading signal: BUY, SELL, or HOLD")
    ticker: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol")
    timestamp: datetime = Field(..., description="ISO 8601 timestamp of signal generation")
    confidence: int = Field(..., ge=1, le=10, description="Confidence level 1-10")