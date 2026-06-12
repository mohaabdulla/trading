from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./tradingbot.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    action = Column(String)  # 'BUY' or 'SELL'
    quantity = Column(Float)
    price = Column(Float)
    commission = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="FILLED") # 'PENDING', 'FILLED', 'CANCELLED'

class AccountSummary(Base):
    __tablename__ = "account_summary"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String, unique=True, index=True)
    net_liquidation = Column(Float, default=0.0)
    total_cash = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    total_commission = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)
