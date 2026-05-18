from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
from datetime import datetime, timezone
import uuid
import enum


def _utcnow():
    return datetime.now(timezone.utc)


class ProviderEnum(str, enum.Enum):
    mercadolivre = "mercadolivre"
    amazon = "amazon"
    shopee = "shopee"
    kabum = "kabum"
    aliexpress = "aliexpress"
    awin = "awin"
    lomadee = "lomadee"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_id = Column(String, unique=True, index=True, nullable=True)
    telegram_id = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)  # None = social/telegram login only
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    searches = relationship("Search", back_populates="user")
    alerts = relationship("PriceAlert", back_populates="user")
    favorites = relationship("Favorite", back_populates="user")


class Search(Base):
    __tablename__ = "searches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    query = Column(String, nullable=False, index=True)
    normalized_query = Column(String, nullable=True)
    results_count = Column(Integer, default=0)
    source = Column(String, default="web")  # web, telegram, api
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User", back_populates="searches")
    offers = relationship("Offer", back_populates="search")


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String, index=True)
    provider = Column(SAEnum(ProviderEnum), nullable=False)
    title = Column(String, nullable=False)
    normalized_title = Column(String, nullable=True)
    category = Column(String, nullable=True)
    brand = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    url = Column(String, nullable=False)
    affiliate_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    offers = relationship("Offer", back_populates="product")
    price_history = relationship("PriceHistory", back_populates="product")


class Offer(Base):
    __tablename__ = "offers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_id = Column(UUID(as_uuid=True), ForeignKey("searches.id"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    provider = Column(SAEnum(ProviderEnum), nullable=False)
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)
    discount_percent = Column(Float, default=0)
    coupon_code = Column(String, nullable=True)
    coupon_discount = Column(Float, default=0)
    cashback_percent = Column(Float, default=0)
    shipping_price = Column(Float, default=0)
    shipping_free = Column(Boolean, default=False)
    final_price = Column(Float, nullable=False)
    score = Column(Float, default=0)
    affiliate_url = Column(String, nullable=False)
    is_fake_discount = Column(Boolean, default=False)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    search = relationship("Search", back_populates="offers")
    product = relationship("Product", back_populates="offers")


class Coupon(Base):
    __tablename__ = "cupons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(SAEnum(ProviderEnum), nullable=False)
    code = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    discount_type = Column(String, default="percent")  # percent, fixed
    discount_value = Column(Float, nullable=False)
    min_purchase = Column(Float, default=0)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class PriceHistory(Base):
    __tablename__ = "historico_preco"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    provider = Column(SAEnum(ProviderEnum), nullable=False)
    price = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    product = relationship("Product", back_populates="price_history")


class PriceAlert(Base):
    __tablename__ = "alertas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    # owner_id: telegram_id real ou bpt_anon_id do browser — obrigatório para scoping
    owner_id = Column(String, nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    query = Column(String, nullable=False)
    target_price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User", back_populates="alerts")


class Favorite(Base):
    __tablename__ = "favoritos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    # owner_id: telegram_id real ou bpt_anon_id do browser — obrigatório para scoping
    owner_id = Column(String, nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User", back_populates="favorites")


class AffiliateClick(Base):
    __tablename__ = "clicks_afiliados"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id"), nullable=False)
    provider = Column(SAEnum(ProviderEnum), nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    clicked_at = Column(DateTime(timezone=True), default=_utcnow, index=True)


class Analytics(Base):
    __tablename__ = "analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String, nullable=False, index=True)
    event_data = Column(JSON, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    session_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)


class ClickEvent(Base):
    __tablename__ = "click_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_id = Column(String, nullable=True, index=True)
    provider = Column(String, nullable=True, index=True)
    product_title = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    affiliate_url = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    referrer = Column(String, nullable=True)
    source = Column(String, default="web")  # web, telegram, tiktok, direct
    clicked_at = Column(DateTime(timezone=True), default=_utcnow, index=True)


class MLToken(Base):
    """
    Stores Mercado Livre OAuth tokens.
    Single row per user_id — upserted on each refresh.
    Tokens stored as-is (HF Space secrets + DB access are already restricted).
    In a production multi-tenant setup these should be AES-256 encrypted.
    """
    __tablename__ = "ml_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, unique=True, index=True, nullable=False)  # ML user_id
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # when access_token expires
    scope = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class ConversionEvent(Base):
    __tablename__ = "conversion_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    click_id = Column(UUID(as_uuid=True), nullable=True)
    external_order_id = Column(String, nullable=True, index=True)  # dedup key (check in code)
    provider = Column(String, nullable=True, index=True)
    product_title = Column(String, nullable=True)
    sale_price = Column(Float, nullable=True)
    commission_rate = Column(Float, nullable=True)
    commission_value = Column(Float, nullable=True)
    status = Column(String, default="pending")  # pending, confirmed, rejected
    converted_at = Column(DateTime(timezone=True), default=_utcnow, index=True)


class ConversionRetryQueue(Base):
    """Queue for failed conversion registrations — retry up to 3 times."""
    __tablename__ = "conversion_retry_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False)
    external_order_id = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)  # full order data to retry
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    resolved = Column(Boolean, default=False)
    error = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class ShortLink(Base):
    """
    Short link for tracked affiliate redirects.
    URL: bestpricetoday.vercel.app/r/{code}
    Flow: user clicks → register analytics → 302 redirect to affiliate URL
    """
    __tablename__ = "short_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(12), unique=True, index=True, nullable=False)  # e.g. "abc123XY"
    affiliate_url = Column(String, nullable=False)  # real affiliate URL
    provider = Column(String, nullable=True)
    product_title = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    source = Column(String, default="video")  # video, telegram, youtube, tiktok, web
    campaign = Column(String, nullable=True)  # e.g. "smartwatch_07h_seg"
    clicks = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    last_clicked_at = Column(DateTime(timezone=True), nullable=True)
