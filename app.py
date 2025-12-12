import warnings
from pydantic.warnings import PydanticDeprecatedSince20

warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)
warnings.filterwarnings("ignore", message=".*Valid config keys have changed in V2.*")
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
model_config = ConfigDict(from_attributes=True)
from typing import Optional, List
from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

# =======================
#  Veritabanı Ayarları
# =======================

DATABASE_URL = "sqlite:///./emlak.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =======================
#  ORM Modelleri
# =======================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    phone = Column(String, unique=True, index=True)
    user_type = Column(String, default="buyer")  # buyer / seller / agent
    city = Column(String, nullable=True)
    district = Column(String, nullable=True)
    neighbourhood = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    requests = relationship("BuyerRequest", back_populates="user")
    offers = relationship("Offer", back_populates="seller")


class BuyerRequest(Base):
    __tablename__ = "buyer_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    description = Column(Text, nullable=True)
    city = Column(String)
    district = Column(String)
    neighbourhood = Column(String)
    budget_min = Column(Float, default=0)
    budget_max = Column(Float)
    room_options = Column(String)  # "3+1,2+1" gibi
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="requests")
    offers = relationship("Offer", back_populates="request")


class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("buyer_requests.id"))
    seller_id = Column(Integer, ForeignKey("users.id"))
    price = Column(Float)
    message = Column(Text, nullable=True)
    photos = Column(Text, nullable=True)  # "url1,url2,url3"
    contact_shared = Column(Boolean, default=False)
    status = Column(String, default="sent")  # sent / accepted / rejected
    created_at = Column(DateTime, default=datetime.utcnow)

    request = relationship("BuyerRequest", back_populates="offers")
    seller = relationship("User", back_populates="offers")
    messages = relationship("Message", back_populates="offer")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, ForeignKey("offers.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    body = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    offer = relationship("Offer", back_populates="messages")


# Tabloyu oluştur
Base.metadata.create_all(bind=engine)


# =======================
#  Pydantic Şemaları
# =======================

class UserCreate(BaseModel):
    name: Optional[str] = None
    phone: str
    user_type: str = "buyer"  # buyer / seller / agent
    city: Optional[str] = None
    district: Optional[str] = None
    neighbourhood: Optional[str] = None


class UserOut(BaseModel):
    id: int
    name: Optional[str]
    phone: str
    user_type: str

    class Config:
        orm_mode = True


class BuyerRequestBase(BaseModel):
    title: str
    description: Optional[str] = None
    city: str
    district: str
    neighbourhood: str
    budget_min: float = 0
    budget_max: float
    room_options: List[str]


class BuyerRequestCreate(BuyerRequestBase):
    user_id: int  # Talebi açan kullanıcının id'si


class BuyerRequestOut(BuyerRequestBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True


class OfferBase(BaseModel):
    price: float
    message: Optional[str] = None
    photos: Optional[List[str]] = None
    contact_shared: bool = False


class OfferCreate(OfferBase):
    seller_id: int  # Teklif veren kullanıcı id'si


class OfferOut(OfferBase):
    id: int
    status: str
    created_at: datetime
    seller_id: int
    request_id: int

    class Config:
        orm_mode = True


class MessageCreate(BaseModel):
    sender_id: int
    body: str


class MessageOut(BaseModel):
    id: int
    sender_id: int
    body: str
    created_at: datetime

    class Config:
        orm_mode = True


# =======================
#  FastAPI Uygulaması
# =======================

app = FastAPI(
    title="Talep Bazlı Emlak API",
    version="1.0.0"
)

# CORS (frontend rahat erişsin diye)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # geliştirmede açık kalsın
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== Basit User endpoint'leri ==========
@app.post("/users", response_model=UserOut)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == user_in.phone).first()
    if user:
        # Zaten kayıtlı ise onu döndür
        return user
    user = User(
        name=user_in.name,
        phone=user_in.phone,
        user_type=user_in.user_type,
        city=user_in.city,
        district=user_in.district,
        neighbourhood=user_in.neighbourhood,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ========== TALep (BuyerRequest) endpoint'leri ==========

@app.post("/requests", response_model=BuyerRequestOut)
def create_request(
    req_in: BuyerRequestCreate, db: Session = Depends(get_db)
):
    user = db.query(User).get(req_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    room_str = ",".join(req_in.room_options)

    req = BuyerRequest(
        user_id=req_in.user_id,
        title=req_in.title,
        description=req_in.description,
        city=req_in.city,
        district=req_in.district,
        neighbourhood=req_in.neighbourhood,
        budget_min=req_in.budget_min,
        budget_max=req_in.budget_max,
        room_options=room_str,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    # Pydantic'e room_options tekrar liste olarak dönsün diye el ile set edelim
    out = BuyerRequestOut.from_orm(req)
    out.room_options = req_in.room_options
    return out


@app.get("/requests", response_model=List[BuyerRequestOut])
def list_requests(
    city: Optional[str] = None,
    district: Optional[str] = None,
    max_budget: Optional[float] = None,
    db: Session = Depends(get_db),
):
    q = db.query(BuyerRequest).filter(BuyerRequest.is_active == True)

    if city:
        q = q.filter(BuyerRequest.city == city)
    if district:
        q = q.filter(BuyerRequest.district == district)
    if max_budget:
        q = q.filter(BuyerRequest.budget_max <= max_budget)

    results = q.order_by(BuyerRequest.created_at.desc()).all()

    out_list = []
    for r in results:
        room_list = r.room_options.split(",") if r.room_options else []
        o = BuyerRequestOut.from_orm(r)
        o.room_options = room_list
        out_list.append(o)
    return out_list


@app.get("/requests/{request_id}", response_model=BuyerRequestOut)
def get_request(request_id: int, db: Session = Depends(get_db)):
    r = db.query(BuyerRequest).get(request_id)
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    room_list = r.room_options.split(",") if r.room_options else []
    o = BuyerRequestOut.from_orm(r)
    o.room_options = room_list
    return o


# ========== OFFER endpoint'leri ==========

@app.post("/requests/{request_id}/offers", response_model=OfferOut)
def create_offer(
    request_id: int,
    offer_in: OfferCreate,
    db: Session = Depends(get_db)
):
    req = db.query(BuyerRequest).get(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    seller = db.query(User).get(offer_in.seller_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")

    photos_str = ",".join(offer_in.photos) if offer_in.photos else None

    offer = Offer(
        request_id=request_id,
        seller_id=offer_in.seller_id,
        price=offer_in.price,
        message=offer_in.message,
        photos=photos_str,
        contact_shared=offer_in.contact_shared,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)

    out = OfferOut.from_orm(offer)
    out.photos = offer_in.photos
    return out


@app.get("/requests/{request_id}/offers", response_model=List[OfferOut])
def list_offers_for_request(
    request_id: int, db: Session = Depends(get_db)
):
    req = db.query(BuyerRequest).get(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    offers = (
        db.query(Offer)
        .filter(Offer.request_id == request_id)
        .order_by(Offer.created_at.desc())
        .all()
    )

    out_list = []
    for off in offers:
        photos = off.photos.split(",") if off.photos else None
        o = OfferOut.from_orm(off)
        o.photos = photos
        out_list.append(o)
    return out_list


@app.patch("/offers/{offer_id}", response_model=OfferOut)
def update_offer_status(
    offer_id: int,
    status: str,
    db: Session = Depends(get_db)
):
    offer = db.query(Offer).get(offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    if status not in ["sent", "accepted", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    offer.status = status
    db.commit()
    db.refresh(offer)

    photos = offer.photos.split(",") if offer.photos else None
    o = OfferOut.from_orm(offer)
    o.photos = photos
    return o


# ========== MESAJ endpoint'leri ==========

@app.post("/offers/{offer_id}/messages", response_model=MessageOut)
def create_message(
    offer_id: int,
    msg_in: MessageCreate,
    db: Session = Depends(get_db)
):
    offer = db.query(Offer).get(offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    sender = db.query(User).get(msg_in.sender_id)
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found")

    msg = Message(
        offer_id=offer_id,
        sender_id=msg_in.sender_id,
        body=msg_in.body,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@app.get("/offers/{offer_id}/messages", response_model=List[MessageOut])
def list_messages(
    offer_id: int, db: Session = Depends(get_db)
):
    offer = db.query(Offer).get(offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    msgs = (
        db.query(Message)
        .filter(Message.offer_id == offer_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return msgs


@app.get("/")
def root():
    return {"message": "Talep bazlı emlak API çalışıyor!"}
