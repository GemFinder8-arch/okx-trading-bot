# 📊 SaaS Dashboard Setup - Complete Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│              Dashboard + User Interface                  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────┐
│                  Backend API (FastAPI)                   │
│         Performance Data + User Management               │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────┐
│              Database (PostgreSQL)                       │
│         Users, Trades, Performance Metrics               │
└─────────────────────────────────────────────────────────┘
```

---

## Phase 1: Backend API Setup (Week 1)

### Step 1: Install Dependencies

```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-jose[cryptography] passlib[bcrypt] python-multipart stripe pydantic email-validator
```

### Step 2: Create Project Structure

```
trading_bot/
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   ├── auth.py
│   └── routes/
│       ├── __init__.py
│       ├── auth.py
│       ├── performance.py
│       ├── trades.py
│       ├── users.py
│       └── subscriptions.py
├── requirements.txt
└── .env
```

### Step 3: Create Database Models

Create `trading_bot/api/models.py`:

```python
from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    full_name = Column(String)
    subscription_tier = Column(String, default="free")  # free, pro, enterprise
    stripe_customer_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    trades = relationship("Trade", back_populates="user")
    performance_snapshots = relationship("PerformanceSnapshot", back_populates="user")

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    symbol = Column(String, index=True)
    side = Column(String)  # BUY or SELL
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    amount = Column(Float)
    pnl_usd = Column(Float, nullable=True)
    pnl_percentage = Column(Float, nullable=True)
    entry_time = Column(DateTime)
    exit_time = Column(DateTime, nullable=True)
    reason = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="trades")

class PerformanceSnapshot(Base):
    __tablename__ = "performance_snapshots"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    date = Column(String, index=True)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    total_pnl_usd = Column(Float, default=0.0)
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="performance_snapshots")

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    stripe_subscription_id = Column(String, unique=True)
    tier = Column(String)  # pro, enterprise
    status = Column(String)  # active, canceled, past_due
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Step 4: Create Database Connection

Create `trading_bot/api/database.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost/trading_bot"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Step 5: Create Authentication

Create `trading_bot/api/auth.py`:

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class TokenData(BaseModel):
    email: Optional[str] = None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        return email
    except JWTError:
        return None
```

### Step 6: Create Schemas

Create `trading_bot/api/schemas.py`:

```python
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    subscription_tier: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class TradeResponse(BaseModel):
    id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: Optional[float]
    pnl_usd: Optional[float]
    pnl_percentage: Optional[float]
    entry_time: datetime
    exit_time: Optional[datetime]
    
    class Config:
        from_attributes = True

class PerformanceResponse(BaseModel):
    date: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl_usd: float
    avg_win: float
    avg_loss: float
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
```

### Step 7: Create API Routes

Create `trading_bot/api/routes/auth.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from trading_bot.api.database import get_db
from trading_bot.api.models import User
from trading_bot.api.schemas import UserCreate, UserResponse, TokenResponse
from trading_bot.api.auth import get_password_hash, verify_password, create_access_token
from datetime import timedelta

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register new user"""
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    new_user = User(
        email=user.email,
        password_hash=get_password_hash(user.password),
        full_name=user.full_name
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.post("/login", response_model=TokenResponse)
async def login(email: str, password: str, db: Session = Depends(get_db)):
    """Login user"""
    user = db.query(User).filter(User.email == email).first()
    
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
```

Create `trading_bot/api/routes/performance.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from trading_bot.api.database import get_db
from trading_bot.api.models import User, Trade, PerformanceSnapshot
from trading_bot.api.auth import decode_token
from typing import List
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/performance", tags=["performance"])

def get_current_user(token: str, db: Session = Depends(get_db)):
    """Get current user from token"""
    email = decode_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@router.get("/summary")
async def get_performance_summary(
    token: str,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get performance summary"""
    user = get_current_user(token, db)
    
    # Get trades from last N days
    start_date = datetime.utcnow() - timedelta(days=days)
    trades = db.query(Trade).filter(
        Trade.user_id == user.id,
        Trade.exit_time >= start_date
    ).all()
    
    if not trades:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "total_pnl_usd": 0.0,
            "avg_daily_profit": 0.0
        }
    
    # Calculate metrics
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t.pnl_usd and t.pnl_usd > 0])
    losing_trades = total_trades - winning_trades
    total_pnl = sum(t.pnl_usd for t in trades if t.pnl_usd)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    avg_daily_profit = total_pnl / days if days > 0 else 0.0
    
    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
        "total_pnl_usd": total_pnl,
        "avg_daily_profit": avg_daily_profit
    }

@router.get("/trades")
async def get_trades(
    token: str,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get recent trades"""
    user = get_current_user(token, db)
    
    trades = db.query(Trade).filter(
        Trade.user_id == user.id
    ).order_by(Trade.entry_time.desc()).limit(limit).all()
    
    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "pnl_usd": t.pnl_usd,
            "pnl_percentage": t.pnl_percentage,
            "entry_time": t.entry_time,
            "exit_time": t.exit_time
        }
        for t in trades
    ]

@router.get("/daily")
async def get_daily_performance(
    token: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get daily performance history"""
    user = get_current_user(token, db)
    
    snapshots = db.query(PerformanceSnapshot).filter(
        PerformanceSnapshot.user_id == user.id
    ).order_by(PerformanceSnapshot.date.desc()).limit(days).all()
    
    return [
        {
            "date": s.date,
            "total_trades": s.total_trades,
            "win_rate": s.win_rate,
            "total_pnl_usd": s.total_pnl_usd,
            "avg_win": s.avg_win,
            "avg_loss": s.avg_loss
        }
        for s in snapshots
    ]
```

### Step 8: Create Main FastAPI App

Create `trading_bot/api/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from trading_bot.api.routes import auth, performance
from trading_bot.api.database import Base, engine

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Trading Bot API",
    description="API for trading bot performance tracking",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(performance.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Step 9: Create .env File

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/trading_bot

# JWT
SECRET_KEY=your-super-secret-key-change-this

# Stripe
STRIPE_API_KEY=sk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### Step 10: Run Backend

```bash
python -m uvicorn trading_bot.api.main:app --reload
```

Visit `http://localhost:8000/docs` to see API documentation.

---

## Phase 2: Frontend Dashboard (Week 2-3)

### Step 1: Create React App

```bash
npx create-react-app trading-dashboard
cd trading-dashboard
npm install recharts axios zustand react-router-dom lucide-react
```

### Step 2: Create API Client

Create `src/api/client.ts`:

```typescript
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authAPI = {
  register: (email: string, password: string, fullName: string) =>
    client.post('/api/auth/register', { email, password, full_name: fullName }),
  login: (email: string, password: string) =>
    client.post('/api/auth/login', { email, password }),
};

export const performanceAPI = {
  getSummary: (days: number = 7) =>
    client.get('/api/performance/summary', { params: { days } }),
  getTrades: (limit: number = 100) =>
    client.get('/api/performance/trades', { params: { limit } }),
  getDaily: (days: number = 30) =>
    client.get('/api/performance/daily', { params: { days } }),
};

export default client;
```

### Step 3: Create Dashboard Component

Create `src/components/Dashboard.tsx`:

```typescript
import React, { useEffect, useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { performanceAPI } from '../api/client';
import { TrendingUp, TrendingDown, DollarSign, Target } from 'lucide-react';

export const Dashboard = () => {
  const [performance, setPerformance] = useState(null);
  const [trades, setTrades] = useState([]);
  const [dailyData, setDailyData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [summaryRes, tradesRes, dailyRes] = await Promise.all([
          performanceAPI.getSummary(7),
          performanceAPI.getTrades(100),
          performanceAPI.getDaily(30),
        ]);

        setPerformance(summaryRes.data);
        setTrades(tradesRes.data);
        setDailyData(dailyRes.data);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) return <div className="p-8">Loading...</div>;

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <h1 className="text-4xl font-bold mb-8">Trading Dashboard</h1>

      {/* Key Metrics */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <MetricCard
          icon={<Target className="w-6 h-6" />}
          label="Win Rate"
          value={`${performance?.win_rate.toFixed(1)}%`}
          color="green"
        />
        <MetricCard
          icon={<DollarSign className="w-6 h-6" />}
          label="Total PnL"
          value={`$${performance?.total_pnl_usd.toFixed(2)}`}
          color={performance?.total_pnl_usd > 0 ? "green" : "red"}
        />
        <MetricCard
          icon={<TrendingUp className="w-6 h-6" />}
          label="Avg Daily"
          value={`$${performance?.avg_daily_profit.toFixed(2)}`}
          color="blue"
        />
        <MetricCard
          icon={<TrendingDown className="w-6 h-6" />}
          label="Total Trades"
          value={performance?.total_trades}
          color="purple"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-8 mb-8">
        <div className="bg-gray-800 p-6 rounded-lg">
          <h2 className="text-xl font-bold mb-4">Daily PnL</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={dailyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="total_pnl_usd" fill="#10b981" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg">
          <h2 className="text-xl font-bold mb-4">Win Rate Trend</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={dailyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="win_rate" stroke="#3b82f6" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Trade History */}
      <div className="bg-gray-800 p-6 rounded-lg">
        <h2 className="text-xl font-bold mb-4">Recent Trades</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left p-2">Symbol</th>
                <th className="text-left p-2">Entry</th>
                <th className="text-left p-2">Exit</th>
                <th className="text-left p-2">PnL</th>
                <th className="text-left p-2">%</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <tr key={trade.id} className="border-b border-gray-700">
                  <td className="p-2">{trade.symbol}</td>
                  <td className="p-2">${trade.entry_price.toFixed(6)}</td>
                  <td className="p-2">${trade.exit_price?.toFixed(6) || '-'}</td>
                  <td className={`p-2 ${trade.pnl_usd > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    ${trade.pnl_usd?.toFixed(2) || '-'}
                  </td>
                  <td className={`p-2 ${trade.pnl_percentage > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {trade.pnl_percentage?.toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

const MetricCard = ({ icon, label, value, color }) => (
  <div className={`bg-gray-800 p-6 rounded-lg border-l-4 border-${color}-500`}>
    <div className="flex items-center justify-between">
      <div>
        <p className="text-gray-400 text-sm">{label}</p>
        <p className="text-2xl font-bold">{value}</p>
      </div>
      <div className={`text-${color}-500`}>{icon}</div>
    </div>
  </div>
);
```

### Step 4: Create Authentication Pages

Create `src/pages/Login.tsx`:

```typescript
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../api/client';

export const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await authAPI.login(email, password);
      localStorage.setItem('token', response.data.access_token);
      navigate('/dashboard');
    } catch (err) {
      setError('Invalid credentials');
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center">
      <div className="bg-gray-800 p-8 rounded-lg w-96">
        <h1 className="text-2xl font-bold text-white mb-6">Login</h1>
        {error && <div className="text-red-500 mb-4">{error}</div>}
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full p-2 mb-4 bg-gray-700 text-white rounded"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full p-2 mb-4 bg-gray-700 text-white rounded"
          />
          <button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white p-2 rounded"
          >
            Login
          </button>
        </form>
      </div>
    </div>
  );
};
```

### Step 5: Create App Router

Create `src/App.tsx`:

```typescript
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Login } from './pages/Login';
import { Dashboard } from './components/Dashboard';

function App() {
  const isAuthenticated = !!localStorage.getItem('token');

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/dashboard"
          element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />}
        />
        <Route path="/" element={<Navigate to="/dashboard" />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

---

## Phase 3: Deployment (Week 4)

### Backend Deployment (Railway)

1. Create account at [railway.app](https://railway.app)
2. Connect GitHub repo
3. Add environment variables
4. Deploy!

### Frontend Deployment (Vercel)

```bash
npm install -g vercel
vercel
```

---

## 💰 Monetization Setup

### Add Stripe Integration

```python
# trading_bot/api/routes/subscriptions.py
import stripe
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])

@router.post("/create-checkout")
async def create_checkout(tier: str, user = Depends(get_current_user)):
    """Create Stripe checkout session"""
    
    prices = {
        "pro": "price_pro_monthly",
        "enterprise": "price_enterprise_monthly"
    }
    
    session = stripe.checkout.Session.create(
        customer_email=user.email,
        payment_method_types=["card"],
        line_items=[
            {
                "price": prices[tier],
                "quantity": 1,
            }
        ],
        mode="subscription",
        success_url="https://yourdomain.com/success",
        cancel_url="https://yourdomain.com/cancel",
    )
    
    return {"checkout_url": session.url}
```

---

## 🎯 Pricing Tiers

- **Free:** $0/month - Last 7 days, basic metrics
- **Pro:** $99/month - Full history, advanced analytics
- **Enterprise:** $499/month - Multiple bots, API access

---

Good luck! 🚀
