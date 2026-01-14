from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base
from app.db.models.enum_utils import enum_values


class TransactionDirection(str, enum.Enum):
    DOMESTIC = "domestic"
    FOREIGN = "foreign"


class TaxpayerYearlyAffiliateTx(Base):
    __tablename__ = "taxpayer_yearly_affiliate_tx"

    id = Column(Integer, primary_key=True, index=True)
    taxpayer_id = Column(Integer, ForeignKey("taxpayer.id", ondelete="CASCADE"), nullable=False, index=True)
    tax_year = Column(Integer, nullable=False, index=True)
    direction = Column(Enum(TransactionDirection, values_callable=enum_values), nullable=False)
    tx_type = Column(String(100), nullable=False)  # e.g., "Penjualan", "Pembelian", "Jasa", "Royalti", "Bunga"
    tx_value = Column(Numeric(20, 2), nullable=True)

    # Relationships
    taxpayer = relationship("Taxpayer", back_populates="yearly_affiliate_txs")
