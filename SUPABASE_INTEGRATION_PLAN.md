# Supabase Integration Plan for Portfolio Navigator Wizard

**Document Version:** 1.0
**Last Updated:** 2026-02-13
**Target Audience:** Development Team, DevOps Engineers
**Estimated Implementation Time:** 2-3 weeks

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Why Supabase?](#why-supabase)
3. [Architecture Overview](#architecture-overview)
4. [Authentication Integration](#authentication-integration)
5. [Database Schema Design](#database-schema-design)
6. [Row-Level Security (RLS) Policies](#row-level-security-rls-policies)
7. [Analytics & Product Intelligence](#analytics--product-intelligence)
8. [Migration Plan](#migration-plan)
9. [Backend Integration](#backend-integration)
10. [Frontend Integration](#frontend-integration)
11. [Security Considerations](#security-considerations)
12. [Cost Analysis](#cost-analysis)
13. [Production Deployment Checklist](#production-deployment-checklist)
14. [Troubleshooting Guide](#troubleshooting-guide)

---

## Executive Summary

This document outlines the comprehensive integration plan for adding **Supabase** to Portfolio Navigator Wizard. Supabase will provide:

- **Authentication & Authorization**: Secure user management with email/password, OAuth, and magic links
- **PostgreSQL Database**: Persistent storage for user profiles, saved portfolios, and preferences
- **Row-Level Security (RLS)**: Database-level authorization ensuring users only access their own data
- **Real-time Subscriptions**: Live updates for portfolio changes and market data
- **Analytics & Insights**: Product intelligence and user behavior tracking
- **Edge Functions**: Serverless compute for background tasks (optional enhancement)

### Current State vs. Future State

| Aspect | Current (Stateless) | With Supabase |
|--------|---------------------|---------------|
| **Authentication** | None (public access) | Email/password, OAuth, magic links |
| **User Data** | None | Persistent user profiles, preferences |
| **Portfolio Storage** | Redis cache only | PostgreSQL with versioning |
| **Authorization** | None | RLS policies, API key management |
| **Analytics** | PostHog (planned) | Supabase Analytics + Custom events |
| **Scalability** | Limited by stateless design | Scales with Postgres + caching |

### Key Benefits

1. **Security**: Production-grade authentication eliminates CVSS 9.8 critical vulnerability
2. **User Experience**: Save portfolios, track history, personalize settings
3. **Product Intelligence**: Understand user behavior, optimize features
4. **Cost Efficiency**: Free tier supports 50,000 monthly active users
5. **Developer Experience**: Auto-generated TypeScript types, instant APIs

---

## Why Supabase?

### Comparison with Alternatives

| Feature | Supabase | Firebase | Auth0 + Custom DB | Custom Build |
|---------|----------|----------|-------------------|--------------|
| **Open Source** | ✅ Yes | ❌ No | Partial | ✅ Yes |
| **Self-hostable** | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| **PostgreSQL** | ✅ Native | ❌ NoSQL | Separate | ✅ Custom |
| **Row-Level Security** | ✅ Built-in | ❌ Manual | ❌ Manual | ⚠️ Complex |
| **Real-time** | ✅ Built-in | ✅ Built-in | ❌ Custom | ⚠️ Complex |
| **Free Tier** | 50K MAU | 10K MAU | 7K MAU | Infrastructure cost |
| **TypeScript Types** | ✅ Auto-generated | Partial | ❌ Manual | ✅ Manual |
| **Learning Curve** | Low | Medium | High | Very High |
| **Time to Implement** | 2-3 weeks | 3-4 weeks | 4-6 weeks | 8-12 weeks |

### Why NOT Custom Authentication?

Building custom auth from scratch requires:

- **Security Expertise**: Password hashing (bcrypt/Argon2), JWT management, CSRF protection, session management
- **Compliance**: GDPR, CCPA, password reset flows, email verification
- **Maintenance**: Security patches, vulnerability monitoring, token rotation
- **Features**: OAuth providers, MFA, magic links, passwordless auth
- **Testing**: Security testing, penetration testing, compliance audits

**Estimated Cost of Custom Auth**: 200-300 engineering hours = $20,000-$40,000 at $100/hour

**Supabase Cost**: $0-$25/month with 1-2 weeks of integration work

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT (React App)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Supabase Auth │  │  Supabase DB │  │   Custom API │          │
│  │   Client     │  │   Client     │  │   (FastAPI)  │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼──────────────────┘
          │                  │                  │
          │ JWT Token        │ Postgres         │ API Calls
          │                  │ Queries          │ (with JWT)
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                        SUPABASE CLOUD                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Auth API   │  │  PostgreSQL  │  │  Realtime    │          │
│  │   (GoTrue)   │  │  (Primary DB)│  │  (Websocket) │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Storage API │  │   Analytics  │  │ Edge Functions│         │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
          │                  │
          │                  │
          ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ JWT Verify   │  │  Redis Cache │  │  Yahoo/Alpha │          │
│  │ Middleware   │  │              │  │  Vantage APIs│          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow: User Authenticates and Saves Portfolio

1. **User Signs In** → Supabase Auth returns JWT token
2. **Client Stores JWT** → localStorage or sessionStorage
3. **Client Makes API Call** → Includes JWT in Authorization header
4. **Backend Verifies JWT** → Validates with Supabase public key
5. **Backend Processes Request** → Optimizes portfolio using cached market data
6. **Backend Saves to Supabase DB** → Inserts portfolio with user_id
7. **RLS Policy Enforces** → Ensures user only sees their own portfolios
8. **Client Receives Response** → Displays saved portfolio

---

## Authentication Integration

### Supported Authentication Methods

#### 1. Email/Password Authentication

**User Flow:**
1. User enters email and password
2. Supabase validates credentials
3. Returns JWT access token + refresh token
4. Client stores tokens and maintains session

**Implementation:**

```typescript
// Frontend: Sign up
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'https://your-project.supabase.co',
  'your-anon-key'
)

async function signUp(email: string, password: string) {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      emailRedirectTo: 'https://portfolionavigator.app/auth/callback',
    },
  })

  if (error) throw error
  return data.user
}

// Frontend: Sign in
async function signIn(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  })

  if (error) throw error
  return data.session
}

// Frontend: Sign out
async function signOut() {
  const { error } = await supabase.auth.signOut()
  if (error) throw error
}
```

#### 2. OAuth Providers

**Supported Providers:**
- Google
- GitHub
- Microsoft
- Apple
- LinkedIn
- GitLab
- Bitbucket
- Discord
- Slack

**Implementation:**

```typescript
// Frontend: OAuth sign in (Google example)
async function signInWithGoogle() {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: 'https://portfolionavigator.app/auth/callback',
      scopes: 'email profile',
      queryParams: {
        access_type: 'offline',
        prompt: 'consent',
      },
    },
  })

  if (error) throw error
  // User is redirected to Google OAuth consent screen
}

// Frontend: OAuth sign in (GitHub example)
async function signInWithGitHub() {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'github',
    options: {
      redirectTo: 'https://portfolionavigator.app/auth/callback',
    },
  })

  if (error) throw error
}
```

**OAuth Configuration (Supabase Dashboard):**

For Google:
1. Go to Google Cloud Console → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID
3. Add authorized redirect URI: `https://your-project.supabase.co/auth/v1/callback`
4. Copy Client ID and Client Secret to Supabase Dashboard → Authentication → Providers → Google

For GitHub:
1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Create new OAuth App
3. Authorization callback URL: `https://your-project.supabase.co/auth/v1/callback`
4. Copy Client ID and Client Secret to Supabase Dashboard

#### 3. Magic Links (Passwordless)

**User Flow:**
1. User enters email
2. Receives email with one-time login link
3. Clicks link → automatically signed in
4. No password required

**Implementation:**

```typescript
// Frontend: Send magic link
async function sendMagicLink(email: string) {
  const { data, error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: 'https://portfolionavigator.app/auth/callback',
    },
  })

  if (error) throw error
  return data
}

// Frontend: Handle callback
// This happens automatically when user clicks magic link
// Supabase client detects the auth token in URL and signs user in
```

#### 4. Multi-Factor Authentication (MFA)

**Setup MFA:**

```typescript
// Frontend: Enroll in MFA (TOTP)
async function enrollMFA() {
  const { data, error } = await supabase.auth.mfa.enroll({
    factorType: 'totp',
    friendlyName: 'Portfolio Navigator App',
  })

  if (error) throw error

  // data contains:
  // - qr_code: QR code SVG for scanning with authenticator app
  // - secret: Manual entry secret
  // - uri: otpauth:// URI

  return data
}

// Frontend: Verify MFA enrollment
async function verifyMFAEnrollment(factorId: string, code: string) {
  const { data, error } = await supabase.auth.mfa.challenge({
    factorId,
  })

  if (error) throw error

  const challengeId = data.id

  const { data: verifyData, error: verifyError } =
    await supabase.auth.mfa.verify({
      factorId,
      challengeId,
      code,
    })

  if (verifyError) throw verifyError
  return verifyData
}

// Frontend: Challenge MFA during login
async function challengeMFA(factorId: string, code: string) {
  const { data, error } = await supabase.auth.mfa.challenge({
    factorId,
  })

  if (error) throw error

  const { data: verifyData, error: verifyError } =
    await supabase.auth.mfa.verify({
      factorId,
      challengeId: data.id,
      code,
    })

  if (verifyError) throw verifyError
  return verifyData
}
```

### Session Management

**Auto-refresh Tokens:**

```typescript
// Frontend: Supabase client automatically refreshes tokens
// No manual intervention required

// Listen for auth state changes
supabase.auth.onAuthStateChange((event, session) => {
  console.log('Auth event:', event, session)

  if (event === 'SIGNED_IN') {
    // User signed in, update UI
  }

  if (event === 'SIGNED_OUT') {
    // User signed out, redirect to login
  }

  if (event === 'TOKEN_REFRESHED') {
    // Token was refreshed, update API calls
  }

  if (event === 'USER_UPDATED') {
    // User profile was updated
  }
})
```

**Get Current Session:**

```typescript
// Frontend: Get current session
const { data: { session }, error } = await supabase.auth.getSession()

if (session) {
  const accessToken = session.access_token
  const user = session.user

  // Use accessToken in API calls to FastAPI backend
  const response = await fetch('/api/portfolios', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  })
}
```

---

## Database Schema Design

### Core Tables

#### 1. User Profiles (`profiles`)

Extends Supabase's built-in `auth.users` table.

```sql
-- Create profiles table
CREATE TABLE public.profiles (
  id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

  -- User Information
  email TEXT UNIQUE NOT NULL,
  full_name TEXT,
  avatar_url TEXT,

  -- User Preferences
  currency TEXT DEFAULT 'USD' NOT NULL,
  theme TEXT DEFAULT 'light' CHECK (theme IN ('light', 'dark', 'auto')),
  risk_tolerance TEXT DEFAULT 'moderate' CHECK (
    risk_tolerance IN ('conservative', 'moderate', 'aggressive')
  ),
  notification_preferences JSONB DEFAULT '{"email": true, "push": false}'::jsonb,

  -- Analytics
  last_login_at TIMESTAMP WITH TIME ZONE,
  login_count INTEGER DEFAULT 0,

  -- Subscription/Plan
  subscription_tier TEXT DEFAULT 'free' CHECK (
    subscription_tier IN ('free', 'basic', 'premium', 'enterprise')
  ),
  subscription_expires_at TIMESTAMP WITH TIME ZONE,

  CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

-- Create indexes
CREATE INDEX idx_profiles_email ON public.profiles(email);
CREATE INDEX idx_profiles_subscription_tier ON public.profiles(subscription_tier);

-- Create trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_profiles_updated_at
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Create trigger to auto-create profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name, avatar_url)
  VALUES (
    NEW.id,
    NEW.email,
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'avatar_url'
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();
```

#### 2. Saved Portfolios (`portfolios`)

Stores user-created portfolios with optimization results.

```sql
-- Create portfolios table
CREATE TABLE public.portfolios (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

  -- Portfolio Metadata
  name TEXT NOT NULL,
  description TEXT,
  is_favorite BOOLEAN DEFAULT false,
  tags TEXT[] DEFAULT '{}',

  -- Portfolio Configuration
  tickers TEXT[] NOT NULL,
  strategy TEXT NOT NULL CHECK (
    strategy IN ('equal_weight', 'max_sharpe', 'min_variance', 'efficient_risk')
  ),
  initial_investment NUMERIC(15, 2) NOT NULL,

  -- Optimization Results
  weights JSONB NOT NULL, -- {"AAPL": 0.25, "GOOGL": 0.30, ...}
  expected_return NUMERIC(10, 6),
  volatility NUMERIC(10, 6),
  sharpe_ratio NUMERIC(10, 6),

  -- Performance Tracking
  backtest_results JSONB, -- Historical performance data
  current_value NUMERIC(15, 2),
  total_return_pct NUMERIC(10, 4),

  -- Sharing
  share_token TEXT UNIQUE, -- For shareable links
  is_public BOOLEAN DEFAULT false,
  view_count INTEGER DEFAULT 0,

  CONSTRAINT valid_name_length CHECK (LENGTH(name) BETWEEN 1 AND 100),
  CONSTRAINT valid_tickers CHECK (array_length(tickers, 1) BETWEEN 3 AND 30),
  CONSTRAINT valid_investment CHECK (initial_investment > 0)
);

-- Create indexes
CREATE INDEX idx_portfolios_user_id ON public.portfolios(user_id);
CREATE INDEX idx_portfolios_created_at ON public.portfolios(created_at DESC);
CREATE INDEX idx_portfolios_share_token ON public.portfolios(share_token)
  WHERE share_token IS NOT NULL;
CREATE INDEX idx_portfolios_tags ON public.portfolios USING GIN(tags);
CREATE INDEX idx_portfolios_strategy ON public.portfolios(strategy);

-- Create trigger to update updated_at
CREATE TRIGGER update_portfolios_updated_at
  BEFORE UPDATE ON public.portfolios
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Create function to generate shareable token
CREATE OR REPLACE FUNCTION generate_share_token()
RETURNS TEXT AS $$
BEGIN
  RETURN encode(gen_random_bytes(16), 'base64url');
END;
$$ LANGUAGE plpgsql;
```

#### 3. Portfolio History (`portfolio_history`)

Tracks changes and performance over time.

```sql
-- Create portfolio_history table
CREATE TABLE public.portfolio_history (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  portfolio_id UUID REFERENCES public.portfolios(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

  -- Snapshot Data
  snapshot_date DATE NOT NULL,
  portfolio_value NUMERIC(15, 2) NOT NULL,
  total_return_pct NUMERIC(10, 4),
  daily_return_pct NUMERIC(10, 4),

  -- Holdings Snapshot
  holdings JSONB NOT NULL, -- {"AAPL": {"shares": 10, "value": 1750.50}, ...}

  CONSTRAINT valid_portfolio_value CHECK (portfolio_value >= 0)
);

-- Create indexes
CREATE INDEX idx_portfolio_history_portfolio_id ON public.portfolio_history(portfolio_id);
CREATE INDEX idx_portfolio_history_snapshot_date ON public.portfolio_history(snapshot_date DESC);
CREATE INDEX idx_portfolio_history_composite ON public.portfolio_history(
  portfolio_id, snapshot_date DESC
);

-- Create unique constraint to prevent duplicate snapshots
CREATE UNIQUE INDEX idx_portfolio_history_unique_snapshot
  ON public.portfolio_history(portfolio_id, snapshot_date);
```

#### 4. User Activity Log (`activity_log`)

Tracks user actions for analytics and debugging.

```sql
-- Create activity_log table
CREATE TABLE public.activity_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

  -- Activity Details
  event_type TEXT NOT NULL, -- 'portfolio_created', 'portfolio_optimized', 'search_performed', etc.
  event_category TEXT NOT NULL CHECK (
    event_category IN ('portfolio', 'search', 'auth', 'settings', 'share', 'export')
  ),
  event_metadata JSONB, -- Additional context

  -- Request Context
  ip_address INET,
  user_agent TEXT,
  referer TEXT,

  -- Performance Metrics
  duration_ms INTEGER, -- How long the action took

  CONSTRAINT valid_event_type CHECK (LENGTH(event_type) > 0)
);

-- Create indexes
CREATE INDEX idx_activity_log_user_id ON public.activity_log(user_id);
CREATE INDEX idx_activity_log_created_at ON public.activity_log(created_at DESC);
CREATE INDEX idx_activity_log_event_type ON public.activity_log(event_type);
CREATE INDEX idx_activity_log_event_category ON public.activity_log(event_category);

-- Create partitioning by month (for large-scale analytics)
-- This is optional but recommended for high-traffic applications
CREATE TABLE public.activity_log_2026_02 PARTITION OF public.activity_log
  FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE public.activity_log_2026_03 PARTITION OF public.activity_log
  FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- Continue creating partitions as needed
```

#### 5. API Keys (`api_keys`)

For programmatic access (advanced users).

```sql
-- Create api_keys table
CREATE TABLE public.api_keys (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

  -- API Key Details
  name TEXT NOT NULL,
  key_hash TEXT UNIQUE NOT NULL, -- bcrypt hash of API key
  key_prefix TEXT NOT NULL, -- First 8 chars for identification (e.g., "pn_live_12345678")

  -- Permissions
  scopes TEXT[] DEFAULT '{"read:portfolios"}', -- Fine-grained permissions

  -- Status
  is_active BOOLEAN DEFAULT true,
  last_used_at TIMESTAMP WITH TIME ZONE,
  expires_at TIMESTAMP WITH TIME ZONE,

  -- Rate Limiting
  rate_limit_per_hour INTEGER DEFAULT 1000,

  CONSTRAINT valid_name_length CHECK (LENGTH(name) BETWEEN 1 AND 50)
);

-- Create indexes
CREATE INDEX idx_api_keys_user_id ON public.api_keys(user_id);
CREATE INDEX idx_api_keys_key_hash ON public.api_keys(key_hash);
CREATE INDEX idx_api_keys_key_prefix ON public.api_keys(key_prefix);

-- Create trigger to update updated_at
CREATE TRIGGER update_api_keys_updated_at
  BEFORE UPDATE ON public.api_keys
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
```

### Database Relationships Diagram

```
┌──────────────────┐
│   auth.users     │
│  (Supabase)      │
└────────┬─────────┘
         │
         │ 1:1
         │
         ▼
┌──────────────────┐         ┌──────────────────┐
│    profiles      │         │   api_keys       │
│  - id            │◄────────┤  - user_id       │
│  - email         │  1:N    │  - key_hash      │
│  - preferences   │         │  - scopes        │
└────────┬─────────┘         └──────────────────┘
         │
         │ 1:N
         │
         ▼
┌──────────────────┐         ┌──────────────────┐
│   portfolios     │         │ portfolio_history│
│  - user_id       │────────►│  - portfolio_id  │
│  - tickers       │  1:N    │  - snapshot_date │
│  - strategy      │         │  - value         │
│  - weights       │         └──────────────────┘
└────────┬─────────┘
         │
         │ 1:N
         │
         ▼
┌──────────────────┐
│  activity_log    │
│  - user_id       │
│  - event_type    │
│  - event_metadata│
└──────────────────┘
```

---

## Row-Level Security (RLS) Policies

Row-Level Security ensures users can only access their own data at the database level, providing defense-in-depth even if application logic has bugs.

### Enable RLS on All Tables

```sql
-- Enable RLS on all user-facing tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.portfolios ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.portfolio_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activity_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;
```

### Profiles Table Policies

```sql
-- Users can view their own profile
CREATE POLICY "Users can view own profile"
  ON public.profiles
  FOR SELECT
  USING (auth.uid() = id);

-- Users can update their own profile
CREATE POLICY "Users can update own profile"
  ON public.profiles
  FOR UPDATE
  USING (auth.uid() = id);

-- Service role can insert profiles (auto-created on signup)
CREATE POLICY "Service role can insert profiles"
  ON public.profiles
  FOR INSERT
  WITH CHECK (auth.uid() = id);

-- Users cannot delete their own profile (must use Supabase auth.deleteUser())
-- This prevents accidental data loss
```

### Portfolios Table Policies

```sql
-- Users can view their own portfolios
CREATE POLICY "Users can view own portfolios"
  ON public.portfolios
  FOR SELECT
  USING (auth.uid() = user_id);

-- Anyone can view public portfolios (via share link)
CREATE POLICY "Anyone can view public portfolios"
  ON public.portfolios
  FOR SELECT
  USING (is_public = true);

-- Users can create portfolios
CREATE POLICY "Users can create portfolios"
  ON public.portfolios
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own portfolios
CREATE POLICY "Users can update own portfolios"
  ON public.portfolios
  FOR UPDATE
  USING (auth.uid() = user_id);

-- Users can delete their own portfolios
CREATE POLICY "Users can delete own portfolios"
  ON public.portfolios
  FOR DELETE
  USING (auth.uid() = user_id);
```

### Portfolio History Policies

```sql
-- Users can view their own portfolio history
CREATE POLICY "Users can view own portfolio history"
  ON public.portfolio_history
  FOR SELECT
  USING (auth.uid() = user_id);

-- System can insert history records (via backend cron job)
CREATE POLICY "Authenticated users can insert portfolio history"
  ON public.portfolio_history
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);
```

### Activity Log Policies

```sql
-- Users can view their own activity logs
CREATE POLICY "Users can view own activity logs"
  ON public.activity_log
  FOR SELECT
  USING (auth.uid() = user_id);

-- System can insert activity logs
CREATE POLICY "Authenticated users can insert activity logs"
  ON public.activity_log
  FOR INSERT
  WITH CHECK (
    auth.uid() = user_id OR user_id IS NULL -- Allow anonymous tracking
  );

-- Users cannot update or delete activity logs (immutable audit trail)
```

### API Keys Policies

```sql
-- Users can view their own API keys
CREATE POLICY "Users can view own API keys"
  ON public.api_keys
  FOR SELECT
  USING (auth.uid() = user_id);

-- Users can create API keys
CREATE POLICY "Users can create API keys"
  ON public.api_keys
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own API keys (revoke, rename)
CREATE POLICY "Users can update own API keys"
  ON public.api_keys
  FOR UPDATE
  USING (auth.uid() = user_id);

-- Users can delete their own API keys
CREATE POLICY "Users can delete own API keys"
  ON public.api_keys
  FOR DELETE
  USING (auth.uid() = user_id);
```

### Testing RLS Policies

```sql
-- Test as authenticated user
SET request.jwt.claims.sub = 'user-uuid-here';

-- This should return only rows where user_id matches
SELECT * FROM public.portfolios;

-- Test as anonymous user (no session)
RESET ALL;

-- This should return only public portfolios
SELECT * FROM public.portfolios;
```

---

## Analytics & Product Intelligence

### Analytics Strategy

**Three-Tier Approach:**

1. **Supabase Analytics**: Built-in usage metrics (API calls, auth events, database queries)
2. **Custom Event Tracking**: User behavior events stored in `activity_log` table
3. **External Analytics** (Optional): Plausible Analytics for privacy-first web analytics

### Supabase Built-in Analytics

**Available Metrics:**
- API requests per second/minute/hour
- Database CPU and memory usage
- Storage bandwidth and space usage
- Authentication events (signups, logins, logouts)
- Real-time connections

**Access Analytics:**
- Supabase Dashboard → Project → Reports
- Export to CSV/JSON
- Prometheus metrics endpoint (Enterprise tier)

### Custom Event Tracking

#### Event Taxonomy

```typescript
// Event Categories
type EventCategory =
  | 'portfolio'   // Portfolio management actions
  | 'search'      // Ticker search, autocomplete
  | 'auth'        // Authentication events
  | 'settings'    // User preference changes
  | 'share'       // Shareable link generation/views
  | 'export'      // Data exports (PDF, CSV)

// Portfolio Events
type PortfolioEvent =
  | 'portfolio_created'
  | 'portfolio_updated'
  | 'portfolio_deleted'
  | 'portfolio_optimized'
  | 'portfolio_viewed'
  | 'portfolio_favorited'
  | 'portfolio_shared'
  | 'portfolio_exported'

// Search Events
type SearchEvent =
  | 'ticker_searched'
  | 'autocomplete_used'
  | 'sector_filtered'
  | 'eligible_tickers_viewed'

// Auth Events
type AuthEvent =
  | 'user_signed_up'
  | 'user_signed_in'
  | 'user_signed_out'
  | 'password_reset_requested'
  | 'email_verified'
  | 'mfa_enabled'

// Settings Events
type SettingsEvent =
  | 'currency_changed'
  | 'theme_changed'
  | 'risk_tolerance_updated'
  | 'notifications_updated'

// Share Events
type ShareEvent =
  | 'share_link_generated'
  | 'share_link_viewed'
  | 'share_link_copied'

// Export Events
type ExportEvent =
  | 'portfolio_exported_pdf'
  | 'portfolio_exported_csv'
  | 'strategy_comparison_exported'
```

#### Event Tracking Implementation

**Backend Function:**

```python
# backend/utils/analytics.py
from typing import Optional, Dict, Any
from datetime import datetime
from supabase import create_client, Client
import os
import json

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

async def track_event(
    user_id: Optional[str],
    event_type: str,
    event_category: str,
    event_metadata: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    referer: Optional[str] = None,
    duration_ms: Optional[int] = None
) -> None:
    """
    Track user activity event to Supabase activity_log table.

    Args:
        user_id: User UUID (None for anonymous events)
        event_type: Specific event (e.g., 'portfolio_created')
        event_category: Event category (e.g., 'portfolio')
        event_metadata: Additional context as JSON
        ip_address: Client IP address
        user_agent: Client user agent string
        referer: HTTP referer
        duration_ms: Action duration in milliseconds
    """
    try:
        data = {
            "user_id": user_id,
            "event_type": event_type,
            "event_category": event_category,
            "event_metadata": event_metadata or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "referer": referer,
            "duration_ms": duration_ms,
            "created_at": datetime.utcnow().isoformat()
        }

        result = supabase.table("activity_log").insert(data).execute()

        # Optional: Also send to external analytics
        # await send_to_plausible(event_type, event_metadata)

    except Exception as e:
        # Never fail the request due to analytics error
        print(f"Analytics tracking error: {e}")

# Example usage in API endpoint
from fastapi import Request
import time

@app.post("/api/portfolios")
async def create_portfolio(request: Request, portfolio: PortfolioCreate):
    start_time = time.time()

    # Get user from JWT token
    user_id = request.state.user_id

    # Create portfolio
    result = await portfolio_service.create(user_id, portfolio)

    # Track event
    duration_ms = int((time.time() - start_time) * 1000)

    await track_event(
        user_id=user_id,
        event_type="portfolio_created",
        event_category="portfolio",
        event_metadata={
            "portfolio_id": result.id,
            "strategy": portfolio.strategy,
            "tickers_count": len(portfolio.tickers),
            "initial_investment": float(portfolio.initial_investment)
        },
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        referer=request.headers.get("referer"),
        duration_ms=duration_ms
    )

    return result
```

**Frontend Tracking:**

```typescript
// frontend/src/utils/analytics.ts
import { supabase } from './supabaseClient'

export async function trackEvent(
  eventType: string,
  eventCategory: string,
  eventMetadata?: Record<string, any>
) {
  try {
    const { data: { user } } = await supabase.auth.getUser()

    await supabase.from('activity_log').insert({
      user_id: user?.id || null,
      event_type: eventType,
      event_category: eventCategory,
      event_metadata: eventMetadata || {},
      created_at: new Date().toISOString(),
    })
  } catch (error) {
    console.error('Analytics tracking error:', error)
    // Never throw - analytics should not break app functionality
  }
}

// Usage example
import { trackEvent } from '@/utils/analytics'

function handlePortfolioCreated(portfolio: Portfolio) {
  trackEvent('portfolio_created', 'portfolio', {
    portfolio_id: portfolio.id,
    strategy: portfolio.strategy,
    tickers_count: portfolio.tickers.length,
  })
}
```

### Analytics Queries

**Most Popular Optimization Strategies:**

```sql
SELECT
  event_metadata->>'strategy' AS strategy,
  COUNT(*) AS usage_count,
  ROUND(AVG((event_metadata->>'tickers_count')::int), 1) AS avg_tickers,
  ROUND(AVG(duration_ms), 0) AS avg_duration_ms
FROM activity_log
WHERE event_type = 'portfolio_optimized'
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY strategy
ORDER BY usage_count DESC;
```

**User Engagement Funnel:**

```sql
WITH user_events AS (
  SELECT
    user_id,
    MAX(CASE WHEN event_type = 'user_signed_up' THEN 1 ELSE 0 END) AS signed_up,
    MAX(CASE WHEN event_type = 'ticker_searched' THEN 1 ELSE 0 END) AS searched,
    MAX(CASE WHEN event_type = 'portfolio_optimized' THEN 1 ELSE 0 END) AS optimized,
    MAX(CASE WHEN event_type = 'portfolio_created' THEN 1 ELSE 0 END) AS saved
  FROM activity_log
  WHERE created_at >= NOW() - INTERVAL '30 days'
    AND user_id IS NOT NULL
  GROUP BY user_id
)
SELECT
  COUNT(*) FILTER (WHERE signed_up = 1) AS total_users,
  COUNT(*) FILTER (WHERE searched = 1) AS searched_users,
  COUNT(*) FILTER (WHERE optimized = 1) AS optimized_users,
  COUNT(*) FILTER (WHERE saved = 1) AS saved_portfolio_users,

  -- Conversion rates
  ROUND(100.0 * COUNT(*) FILTER (WHERE searched = 1) / NULLIF(COUNT(*) FILTER (WHERE signed_up = 1), 0), 2) AS search_rate,
  ROUND(100.0 * COUNT(*) FILTER (WHERE optimized = 1) / NULLIF(COUNT(*) FILTER (WHERE searched = 1), 0), 2) AS optimization_rate,
  ROUND(100.0 * COUNT(*) FILTER (WHERE saved = 1) / NULLIF(COUNT(*) FILTER (WHERE optimized = 1), 0), 2) AS save_rate
FROM user_events;
```

**Performance Monitoring:**

```sql
SELECT
  event_type,
  event_category,
  COUNT(*) AS event_count,
  ROUND(AVG(duration_ms), 0) AS avg_duration_ms,
  ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY duration_ms), 0) AS p50_duration_ms,
  ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms), 0) AS p95_duration_ms,
  ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms), 0) AS p99_duration_ms,
  MAX(duration_ms) AS max_duration_ms
FROM activity_log
WHERE created_at >= NOW() - INTERVAL '7 days'
  AND duration_ms IS NOT NULL
GROUP BY event_type, event_category
ORDER BY avg_duration_ms DESC;
```

### Comparison: Analytics Solutions

| Feature | Supabase Analytics | Plausible Analytics | Google Analytics | PostHog |
|---------|-------------------|---------------------|------------------|---------|
| **Privacy** | Full control | GDPR-compliant | Cookie-based | Self-hostable |
| **Real-time** | Yes (via Postgres) | Yes | Delayed (4-24 hours) | Yes |
| **Custom Events** | Unlimited | Limited | Yes | Unlimited |
| **Session Replay** | No | No | No | Yes (privacy risk) |
| **Funnel Analysis** | Custom SQL | Basic | Yes | Yes |
| **Cost** | Free tier | €9/month | Free | €0-450/month |
| **Data Ownership** | You own it | Plausible stores | Google owns | You own it |
| **Cookie-free** | Yes | Yes | No | Optional |
| **Open Source** | Yes | Yes | No | Yes |

**Recommendation for Portfolio Navigator:**

1. **Primary**: Supabase `activity_log` table for custom events (full control, no extra cost)
2. **Secondary**: Plausible Analytics for web analytics (page views, referrers, countries)
3. **Avoid**: Google Analytics (cookie consent required, privacy concerns)
4. **Avoid**: PostHog (session replay is privacy risk for financial app)

---

## Migration Plan

### Phase 1: Supabase Setup (Week 1)

**Day 1-2: Infrastructure Setup**

1. Create Supabase Project
   - Go to https://supabase.com/dashboard
   - Click "New Project"
   - Choose organization and region (use same region as Railway Redis)
   - Set database password (store in 1Password/Bitwarden)
   - Wait for project provisioning (~2 minutes)

2. Configure Authentication
   - Dashboard → Authentication → Providers
   - Enable Email provider (default)
   - Configure email templates (welcome email, password reset, magic link)
   - Add OAuth providers:
     - Google: Add Client ID/Secret from Google Cloud Console
     - GitHub: Add Client ID/Secret from GitHub OAuth Apps
   - Configure redirect URLs:
     - Production: `https://portfolionavigator.app/auth/callback`
     - Local: `http://localhost:5173/auth/callback`

3. Set Environment Variables
   ```bash
   # .env file
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... # Keep secret!
   SUPABASE_JWT_SECRET=your-jwt-secret
   ```

**Day 3-4: Database Schema**

1. Run SQL migrations in Supabase SQL Editor
   - Create `profiles` table with RLS
   - Create `portfolios` table with RLS
   - Create `portfolio_history` table with RLS
   - Create `activity_log` table with RLS
   - Create `api_keys` table with RLS
   - Create all indexes and triggers

2. Test RLS Policies
   - Create test user via Supabase Dashboard
   - Insert test data
   - Verify user can only see own data
   - Verify public portfolio sharing works

**Day 5-7: Backend Integration**

1. Install Supabase Python Client
   ```bash
   pip install supabase
   ```

2. Create Supabase Client Service
   ```python
   # backend/utils/supabase_client.py
   from supabase import create_client, Client
   import os

   SUPABASE_URL = os.getenv("SUPABASE_URL")
   SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

   supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
   ```

3. Create JWT Verification Middleware
   ```python
   # backend/middleware/auth.py
   from fastapi import Request, HTTPException, status
   from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
   import jwt
   import os

   security = HTTPBearer()

   async def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
       token = credentials.credentials

       try:
           # Verify JWT using Supabase JWT secret
           payload = jwt.decode(
               token,
               os.getenv("SUPABASE_JWT_SECRET"),
               algorithms=["HS256"],
               audience="authenticated"
           )

           user_id = payload.get("sub")
           if not user_id:
               raise HTTPException(
                   status_code=status.HTTP_401_UNAUTHORIZED,
                   detail="Invalid token"
               )

           return user_id

       except jwt.ExpiredSignatureError:
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail="Token expired"
           )
       except jwt.InvalidTokenError:
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail="Invalid token"
           )
   ```

4. Update API Endpoints
   ```python
   # backend/routers/portfolio.py
   from middleware.auth import verify_jwt

   @app.post("/api/portfolios", dependencies=[Depends(verify_jwt)])
   async def create_portfolio(
       portfolio: PortfolioCreate,
       user_id: str = Depends(verify_jwt)
   ):
       # Save to Supabase instead of just Redis
       result = await supabase.table("portfolios").insert({
           "user_id": user_id,
           "name": portfolio.name,
           "tickers": portfolio.tickers,
           "strategy": portfolio.strategy,
           "initial_investment": portfolio.initial_investment,
           "weights": portfolio.weights,
           "expected_return": portfolio.expected_return,
           "volatility": portfolio.volatility,
           "sharpe_ratio": portfolio.sharpe_ratio
       }).execute()

       return result.data[0]
   ```

### Phase 2: Frontend Integration (Week 2)

**Day 1-3: Authentication UI**

1. Install Supabase JS Client
   ```bash
   npm install @supabase/supabase-js
   ```

2. Create Supabase Client
   ```typescript
   // frontend/src/utils/supabaseClient.ts
   import { createClient } from '@supabase/supabase-js'

   const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
   const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

   export const supabase = createClient(supabaseUrl, supabaseAnonKey)
   ```

3. Create Auth Context
   ```typescript
   // frontend/src/contexts/AuthContext.tsx
   import { createContext, useContext, useEffect, useState } from 'react'
   import { User, Session } from '@supabase/supabase-js'
   import { supabase } from '@/utils/supabaseClient'

   interface AuthContextType {
     user: User | null
     session: Session | null
     signIn: (email: string, password: string) => Promise<void>
     signUp: (email: string, password: string) => Promise<void>
     signOut: () => Promise<void>
     loading: boolean
   }

   const AuthContext = createContext<AuthContextType | undefined>(undefined)

   export function AuthProvider({ children }: { children: React.ReactNode }) {
     const [user, setUser] = useState<User | null>(null)
     const [session, setSession] = useState<Session | null>(null)
     const [loading, setLoading] = useState(true)

     useEffect(() => {
       // Get initial session
       supabase.auth.getSession().then(({ data: { session } }) => {
         setSession(session)
         setUser(session?.user ?? null)
         setLoading(false)
       })

       // Listen for auth changes
       const { data: { subscription } } = supabase.auth.onAuthStateChange(
         (_event, session) => {
           setSession(session)
           setUser(session?.user ?? null)
         }
       )

       return () => subscription.unsubscribe()
     }, [])

     const signIn = async (email: string, password: string) => {
       const { error } = await supabase.auth.signInWithPassword({
         email,
         password,
       })
       if (error) throw error
     }

     const signUp = async (email: string, password: string) => {
       const { error } = await supabase.auth.signUp({
         email,
         password,
       })
       if (error) throw error
     }

     const signOut = async () => {
       const { error } = await supabase.auth.signOut()
       if (error) throw error
     }

     return (
       <AuthContext.Provider value={{ user, session, signIn, signUp, signOut, loading }}>
         {children}
       </AuthContext.Provider>
     )
   }

   export const useAuth = () => {
     const context = useContext(AuthContext)
     if (!context) throw new Error('useAuth must be used within AuthProvider')
     return context
   }
   ```

4. Create Login/Signup Components
   ```typescript
   // frontend/src/components/auth/LoginForm.tsx
   import { useState } from 'react'
   import { useAuth } from '@/contexts/AuthContext'

   export function LoginForm() {
     const [email, setEmail] = useState('')
     const [password, setPassword] = useState('')
     const [error, setError] = useState('')
     const { signIn } = useAuth()

     async function handleSubmit(e: React.FormEvent) {
       e.preventDefault()
       try {
         await signIn(email, password)
       } catch (err) {
         setError(err.message)
       }
     }

     return (
       <form onSubmit={handleSubmit}>
         <input
           type="email"
           value={email}
           onChange={(e) => setEmail(e.target.value)}
           placeholder="Email"
           required
         />
         <input
           type="password"
           value={password}
           onChange={(e) => setPassword(e.target.value)}
           placeholder="Password"
           required
         />
         <button type="submit">Sign In</button>
         {error && <p>{error}</p>}
       </form>
     )
   }
   ```

**Day 4-5: Update API Calls**

1. Create Authenticated Fetch Wrapper
   ```typescript
   // frontend/src/utils/api.ts
   import { supabase } from './supabaseClient'

   export async function authenticatedFetch(
     url: string,
     options: RequestInit = {}
   ) {
     const { data: { session } } = await supabase.auth.getSession()

     if (!session) {
       throw new Error('Not authenticated')
     }

     const response = await fetch(url, {
       ...options,
       headers: {
         ...options.headers,
         'Authorization': `Bearer ${session.access_token}`,
         'Content-Type': 'application/json',
       },
     })

     if (!response.ok) {
       throw new Error(`API error: ${response.statusText}`)
     }

     return response.json()
   }
   ```

2. Update Portfolio API Calls
   ```typescript
   // frontend/src/services/portfolioService.ts
   import { authenticatedFetch } from '@/utils/api'

   export async function createPortfolio(portfolio: PortfolioCreate) {
     return authenticatedFetch('/api/portfolios', {
       method: 'POST',
       body: JSON.stringify(portfolio),
     })
   }

   export async function getUserPortfolios() {
     return authenticatedFetch('/api/portfolios')
   }

   export async function updatePortfolio(id: string, updates: Partial<Portfolio>) {
     return authenticatedFetch(`/api/portfolios/${id}`, {
       method: 'PATCH',
       body: JSON.stringify(updates),
     })
   }

   export async function deletePortfolio(id: string) {
     return authenticatedFetch(`/api/portfolios/${id}`, {
       method: 'DELETE',
     })
   }
   ```

**Day 6-7: User Dashboard**

1. Create Dashboard Page
   ```typescript
   // frontend/src/pages/Dashboard.tsx
   import { useEffect, useState } from 'react'
   import { useAuth } from '@/contexts/AuthContext'
   import { getUserPortfolios } from '@/services/portfolioService'

   export function Dashboard() {
     const { user } = useAuth()
     const [portfolios, setPortfolios] = useState([])
     const [loading, setLoading] = useState(true)

     useEffect(() => {
       async function loadPortfolios() {
         try {
           const data = await getUserPortfolios()
           setPortfolios(data)
         } catch (error) {
           console.error('Failed to load portfolios:', error)
         } finally {
           setLoading(false)
         }
       }

       loadPortfolios()
     }, [])

     if (loading) return <div>Loading...</div>

     return (
       <div>
         <h1>Welcome, {user?.email}</h1>
         <h2>Your Portfolios</h2>
         {portfolios.length === 0 ? (
           <p>No portfolios yet. Create your first portfolio!</p>
         ) : (
           <ul>
             {portfolios.map((portfolio) => (
               <li key={portfolio.id}>{portfolio.name}</li>
             ))}
           </ul>
         )}
       </div>
     )
   }
   ```

### Phase 3: Analytics & Monitoring (Week 3)

**Day 1-2: Implement Event Tracking**

1. Create analytics utility (see code in Analytics section above)
2. Add tracking to all major user actions
3. Test event logging in Supabase dashboard

**Day 3-4: Build Analytics Dashboard**

1. Create admin dashboard for viewing analytics
2. Add charts for:
   - Daily active users
   - Portfolio creations over time
   - Strategy distribution
   - Performance metrics (P50, P95, P99 latencies)

**Day 5-7: Optional Enhancements**

1. Set up Plausible Analytics for web analytics
2. Create scheduled jobs for:
   - Daily portfolio value snapshots
   - Weekly usage reports
   - Monthly cohort analysis

### Phase 4: Testing & Deployment

**Testing Checklist:**

- [ ] Unit tests for auth middleware
- [ ] Integration tests for API endpoints with auth
- [ ] E2E tests for signup/login/logout flows
- [ ] RLS policy tests
- [ ] Load testing with authenticated users
- [ ] Security audit (SQL injection, XSS, CSRF)

**Deployment Steps:**

1. Set environment variables in Railway
2. Run database migrations in Supabase
3. Deploy backend with auth middleware
4. Deploy frontend with Supabase client
5. Test in staging environment
6. Gradual rollout (10% → 50% → 100%)
7. Monitor error rates and performance

---

## Backend Integration

### Install Dependencies

```bash
# Python dependencies
pip install supabase==2.3.0
pip install pyjwt==2.8.0
pip install python-jose[cryptography]==3.3.0

# Update requirements.txt
supabase==2.3.0
pyjwt==2.8.0
python-jose[cryptography]==3.3.0
```

### Environment Variables

```bash
# .env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... # Secret! Server-side only
SUPABASE_JWT_SECRET=your-jwt-secret-from-supabase-settings
```

### Supabase Client Setup

```python
# backend/utils/supabase_client.py
from supabase import create_client, Client
from typing import Optional
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Client for server-side operations (uses service role key)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Client for user-context operations (uses anon key)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def get_supabase_client(user_jwt: Optional[str] = None) -> Client:
    """
    Get Supabase client with optional user JWT for RLS context.

    Args:
        user_jwt: User's access token from Supabase auth

    Returns:
        Supabase client configured for the user context
    """
    if user_jwt:
        client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        client.auth.set_session(user_jwt, None)
        return client
    return supabase
```

### JWT Authentication Middleware

```python
# backend/middleware/supabase_auth.py
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Optional, Dict, Any
import os

security = HTTPBearer()

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Verify Supabase JWT and extract user information.

    Returns:
        Dict containing user_id, email, role, etc.

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials

    try:
        # Decode and verify JWT
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_aud": True}
        )

        # Extract user information
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role", "authenticated")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {
            "user_id": user_id,
            "email": email,
            "role": role,
            "raw_payload": payload
        }

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[Dict[str, Any]]:
    """
    Optional authentication - returns None if no token provided.
    Useful for endpoints that work with or without authentication.
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
```

### Update API Endpoints

```python
# backend/routers/portfolio.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from middleware.supabase_auth import get_current_user, get_optional_user
from utils.supabase_client import supabase_admin
from utils.analytics import track_event
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import time

router = APIRouter(prefix="/api/portfolios", tags=["portfolios"])

class PortfolioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    tickers: List[str]
    strategy: str
    initial_investment: float

class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_favorite: Optional[bool] = None
    tags: Optional[List[str]] = None

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    request: Request,
    portfolio: PortfolioCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new portfolio (requires authentication)"""
    start_time = time.time()
    user_id = current_user["user_id"]

    try:
        # 1. Validate tickers (existing logic)
        # ...

        # 2. Optimize portfolio (existing logic)
        optimization_result = await optimize_portfolio(
            portfolio.tickers,
            portfolio.strategy,
            portfolio.initial_investment
        )

        # 3. Save to Supabase
        result = supabase_admin.table("portfolios").insert({
            "user_id": user_id,
            "name": portfolio.name,
            "description": portfolio.description,
            "tickers": portfolio.tickers,
            "strategy": portfolio.strategy,
            "initial_investment": float(portfolio.initial_investment),
            "weights": optimization_result["weights"],
            "expected_return": optimization_result["expected_return"],
            "volatility": optimization_result["volatility"],
            "sharpe_ratio": optimization_result["sharpe_ratio"],
        }).execute()

        portfolio_data = result.data[0]

        # 4. Track analytics event
        duration_ms = int((time.time() - start_time) * 1000)
        await track_event(
            user_id=user_id,
            event_type="portfolio_created",
            event_category="portfolio",
            event_metadata={
                "portfolio_id": portfolio_data["id"],
                "strategy": portfolio.strategy,
                "tickers_count": len(portfolio.tickers),
                "initial_investment": float(portfolio.initial_investment)
            },
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            duration_ms=duration_ms
        )

        return portfolio_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create portfolio: {str(e)}"
        )

@router.get("/")
async def get_user_portfolios(
    current_user: Dict[str, Any] = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """Get all portfolios for the authenticated user"""
    user_id = current_user["user_id"]

    try:
        result = supabase_admin.table("portfolios") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        return {
            "portfolios": result.data,
            "count": len(result.data)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch portfolios: {str(e)}"
        )

@router.get("/{portfolio_id}")
async def get_portfolio(
    portfolio_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """Get a specific portfolio (public if shared, otherwise requires auth)"""
    try:
        result = supabase_admin.table("portfolios") \
            .select("*") \
            .eq("id", portfolio_id) \
            .single() \
            .execute()

        portfolio = result.data

        # Check access permissions
        if portfolio["is_public"]:
            # Public portfolio - anyone can view
            # Increment view count
            supabase_admin.table("portfolios") \
                .update({"view_count": portfolio["view_count"] + 1}) \
                .eq("id", portfolio_id) \
                .execute()

            return portfolio
        else:
            # Private portfolio - must be owner
            if not current_user or current_user["user_id"] != portfolio["user_id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
            return portfolio

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

@router.patch("/{portfolio_id}")
async def update_portfolio(
    portfolio_id: str,
    updates: PortfolioUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update a portfolio (requires authentication and ownership)"""
    user_id = current_user["user_id"]

    try:
        # Build update dict (only include fields that were provided)
        update_data = updates.dict(exclude_unset=True)

        # Perform update with RLS ensuring user owns the portfolio
        result = supabase_admin.table("portfolios") \
            .update(update_data) \
            .eq("id", portfolio_id) \
            .eq("user_id", user_id) \
            .execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found or access denied"
            )

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update portfolio: {str(e)}"
        )

@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a portfolio (requires authentication and ownership)"""
    user_id = current_user["user_id"]

    try:
        result = supabase_admin.table("portfolios") \
            .delete() \
            .eq("id", portfolio_id) \
            .eq("user_id", user_id) \
            .execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found or access denied"
            )

        # Track deletion event
        await track_event(
            user_id=user_id,
            event_type="portfolio_deleted",
            event_category="portfolio",
            event_metadata={"portfolio_id": portfolio_id}
        )

        return {"message": "Portfolio deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete portfolio: {str(e)}"
        )

@router.post("/{portfolio_id}/share")
async def create_share_link(
    portfolio_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Generate a shareable link for a portfolio"""
    user_id = current_user["user_id"]

    try:
        # Generate unique share token
        result = supabase_admin.rpc("generate_share_token").execute()
        share_token = result.data

        # Update portfolio to be public with share token
        update_result = supabase_admin.table("portfolios") \
            .update({
                "is_public": True,
                "share_token": share_token
            }) \
            .eq("id", portfolio_id) \
            .eq("user_id", user_id) \
            .execute()

        if not update_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found or access denied"
            )

        portfolio = update_result.data[0]
        share_url = f"https://portfolionavigator.app/share/{share_token}"

        # Track share event
        await track_event(
            user_id=user_id,
            event_type="share_link_generated",
            event_category="share",
            event_metadata={
                "portfolio_id": portfolio_id,
                "share_token": share_token
            }
        )

        return {
            "share_url": share_url,
            "share_token": share_token
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create share link: {str(e)}"
        )
```

---

## Frontend Integration

### Install Dependencies

```bash
npm install @supabase/supabase-js@2.39.0
```

### Environment Variables

```bash
# .env.local (for local development)
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Supabase Client Setup

```typescript
// frontend/src/utils/supabaseClient.ts
import { createClient } from '@supabase/supabase-js'
import type { Database } from '@/types/supabase'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables')
}

export const supabase = createClient<Database>(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
    storage: window.localStorage,
  },
})
```

### TypeScript Types (Auto-generated)

```bash
# Generate TypeScript types from Supabase schema
npx supabase gen types typescript --project-id your-project-ref > src/types/supabase.ts
```

Example generated types:

```typescript
// frontend/src/types/supabase.ts
export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string
          created_at: string
          updated_at: string
          email: string
          full_name: string | null
          avatar_url: string | null
          currency: string
          theme: string
          risk_tolerance: string
          notification_preferences: Json
          subscription_tier: string
          subscription_expires_at: string | null
        }
        Insert: {
          id: string
          email: string
          full_name?: string | null
          avatar_url?: string | null
          currency?: string
          theme?: string
          risk_tolerance?: string
          notification_preferences?: Json
          subscription_tier?: string
        }
        Update: {
          full_name?: string | null
          avatar_url?: string | null
          currency?: string
          theme?: string
          risk_tolerance?: string
          notification_preferences?: Json
        }
      }
      portfolios: {
        Row: {
          id: string
          user_id: string
          created_at: string
          updated_at: string
          name: string
          description: string | null
          is_favorite: boolean
          tags: string[]
          tickers: string[]
          strategy: string
          initial_investment: number
          weights: Json
          expected_return: number | null
          volatility: number | null
          sharpe_ratio: number | null
          backtest_results: Json | null
          current_value: number | null
          total_return_pct: number | null
          share_token: string | null
          is_public: boolean
          view_count: number
        }
        Insert: {
          user_id: string
          name: string
          description?: string | null
          tickers: string[]
          strategy: string
          initial_investment: number
          weights: Json
          expected_return?: number | null
          volatility?: number | null
          sharpe_ratio?: number | null
        }
        Update: {
          name?: string
          description?: string | null
          is_favorite?: boolean
          tags?: string[]
        }
      }
    }
    Views: {}
    Functions: {
      generate_share_token: {
        Args: {}
        Returns: string
      }
    }
  }
}
```

### Auth Context Provider

See code in "Authentication Integration" section above for full `AuthContext.tsx` implementation.

### Protected Routes

```typescript
// frontend/src/components/auth/ProtectedRoute.tsx
import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

export function ProtectedRoute() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}

// Usage in App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from '@/contexts/AuthContext'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { Dashboard } from '@/pages/Dashboard'
import { Login } from '@/pages/Login'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          {/* Protected routes */}
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/portfolios" element={<Portfolios />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
```

### API Service with Authentication

```typescript
// frontend/src/services/api.ts
import { supabase } from '@/utils/supabaseClient'

class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any
  ) {
    super(message)
    this.name = 'APIError'
  }
}

async function authenticatedFetch<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  // Get current session
  const { data: { session }, error } = await supabase.auth.getSession()

  if (error || !session) {
    throw new APIError('Not authenticated', 401)
  }

  // Make request with access token
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${session.access_token}`,
      'Content-Type': 'application/json',
    },
  })

  // Handle errors
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new APIError(
      errorData.detail || response.statusText,
      response.status,
      errorData
    )
  }

  return response.json()
}

// Portfolio API functions
export const portfolioAPI = {
  create: async (portfolio: PortfolioCreate) => {
    return authenticatedFetch<Portfolio>('/api/portfolios', {
      method: 'POST',
      body: JSON.stringify(portfolio),
    })
  },

  list: async (limit = 50, offset = 0) => {
    return authenticatedFetch<{ portfolios: Portfolio[]; count: number }>(
      `/api/portfolios?limit=${limit}&offset=${offset}`
    )
  },

  get: async (id: string) => {
    return authenticatedFetch<Portfolio>(`/api/portfolios/${id}`)
  },

  update: async (id: string, updates: Partial<Portfolio>) => {
    return authenticatedFetch<Portfolio>(`/api/portfolios/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    })
  },

  delete: async (id: string) => {
    return authenticatedFetch<{ message: string }>(`/api/portfolios/${id}`, {
      method: 'DELETE',
    })
  },

  createShareLink: async (id: string) => {
    return authenticatedFetch<{ share_url: string; share_token: string }>(
      `/api/portfolios/${id}/share`,
      { method: 'POST' }
    )
  },
}
```

---

## Security Considerations

### 1. JWT Security

**Best Practices:**
- ✅ Always verify JWT signature using `SUPABASE_JWT_SECRET`
- ✅ Check token expiration (`exp` claim)
- ✅ Validate audience (`aud` claim should be "authenticated")
- ✅ Never expose `SUPABASE_SERVICE_KEY` in frontend code
- ✅ Use HTTPS in production to prevent token interception
- ✅ Set reasonable token expiration (default: 1 hour)
- ✅ Implement refresh token rotation

**Token Storage:**
- ✅ Store tokens in `httpOnly` cookies (most secure, but requires CORS setup)
- ⚠️ localStorage (vulnerable to XSS, but convenient for SPA)
- ❌ Never store in sessionStorage or URL parameters

### 2. Row-Level Security (RLS)

**Defense in Depth:**
- Even if backend auth middleware has bugs, RLS prevents unauthorized data access
- Always enable RLS on all user-facing tables
- Test RLS policies thoroughly using `SET request.jwt.claims.sub = 'user-id'`

**Common RLS Mistakes:**
- ❌ Forgetting to enable RLS on new tables
- ❌ Using `user_id = current_setting('request.jwt.claims.sub')` (old pattern, use `auth.uid()`)
- ❌ Not testing RLS with anonymous users
- ❌ Overly permissive policies (e.g., allowing users to see all data)

### 3. API Security

**Rate Limiting:**
- Already implemented via SlowAPI middleware
- Additional per-user rate limits via `api_keys` table
- Monitor for abuse patterns in activity logs

**Input Validation:**
- Already implemented via `validation.py` middleware
- Additional validation at database level (CHECK constraints)
- Sanitize HTML in user-generated content

**CORS Configuration:**

```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://portfolionavigator.app",
        "http://localhost:5173"  # Remove in production
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,  # Cache preflight requests for 1 hour
)
```

### 4. Data Privacy

**PII Handling:**
- Email addresses are PII - handle according to GDPR/CCPA
- Do not log sensitive data (passwords, tokens, API keys)
- Implement data export feature (GDPR right to data portability)
- Implement account deletion feature (GDPR right to be forgotten)

**Encryption:**
- ✅ All data encrypted at rest (Supabase uses AES-256)
- ✅ All data encrypted in transit (TLS 1.3)
- ❌ Do NOT implement custom encryption (use Supabase's built-in encryption)

### 5. Compliance Checklist

**GDPR Compliance:**
- [ ] Cookie consent banner (if using tracking cookies)
- [ ] Privacy policy published
- [ ] Data export endpoint (`GET /api/users/me/export`)
- [ ] Account deletion endpoint (`DELETE /api/users/me`)
- [ ] Data breach notification process
- [ ] Data processing agreement (DPA) with Supabase

**Security Headers:**
Already implemented via `security.py` middleware:
- ✅ Strict-Transport-Security (HSTS)
- ✅ Content-Security-Policy (CSP)
- ✅ X-Content-Type-Options: nosniff
- ✅ X-Frame-Options: DENY
- ✅ Referrer-Policy: strict-origin-when-cross-origin

---

## Cost Analysis

### Supabase Pricing Tiers

| Feature | Free | Pro | Team | Enterprise |
|---------|------|-----|------|------------|
| **Database** | 500 MB | 8 GB | 8 GB | Custom |
| **Storage** | 1 GB | 100 GB | 100 GB | Custom |
| **Bandwidth** | 5 GB | 250 GB | 250 GB | Custom |
| **Monthly Active Users** | 50,000 | Unlimited | Unlimited | Unlimited |
| **Auth MAU** | 50,000 | 100,000 | 100,000 | Custom |
| **Edge Functions** | 500K invocations | 2M invocations | 2M invocations | Custom |
| **Support** | Community | Email | Priority | Dedicated |
| **Cost** | **$0/month** | **$25/month** | **$599/month** | Custom |

### Cost Estimation for Portfolio Navigator

**Assumptions:**
- 1,000 monthly active users
- Average 10 portfolios per user = 10,000 portfolios
- Average portfolio size: 2 KB (tickers, weights, metadata)
- Average 50 API calls per user per session
- Average session duration: 10 minutes

**Database Storage:**
- Profiles: 1,000 users × 1 KB = 1 MB
- Portfolios: 10,000 portfolios × 2 KB = 20 MB
- Activity logs: 50,000 events/month × 0.5 KB = 25 MB
- Total: ~50 MB (well within free tier 500 MB limit)

**Bandwidth:**
- API calls: 1,000 users × 50 calls × 5 KB = 250 MB/month
- Total: ~250 MB (well within free tier 5 GB limit)

**Conclusion:**
- **Recommended Tier**: Free tier is sufficient for first 1,000-5,000 users
- **Upgrade Trigger**: When approaching 50 GB database or 5 GB bandwidth
- **Estimated Timeline**: 6-12 months before needing Pro tier ($25/month)

### Total Infrastructure Cost Comparison

| Component | Current | With Supabase Free | With Supabase Pro |
|-----------|---------|-------------------|-------------------|
| **Backend Hosting** (Railway) | $5-10/month | $5-10/month | $5-10/month |
| **Redis Cache** (Railway) | $5/month | $5/month | $5/month |
| **Database** | $0 (none) | $0 | $25/month |
| **Authentication** | $0 (none) | $0 | $0 |
| **Analytics** | $0 (none) | $0 | $0 |
| **Total** | **$10-15/month** | **$10-15/month** | **$35-40/month** |

**ROI Analysis:**
- Custom auth implementation: $20,000-$40,000 upfront + maintenance
- Supabase: $0 upfront + $0-25/month ongoing
- **Savings**: $20,000+ in first year

---

## Production Deployment Checklist

### Pre-Deployment

- [ ] Run all database migrations in Supabase
- [ ] Enable RLS on all tables
- [ ] Test RLS policies with test users
- [ ] Configure OAuth providers (Google, GitHub)
- [ ] Set up email templates in Supabase Auth
- [ ] Configure CORS allowlist in backend
- [ ] Set all environment variables in Railway
- [ ] Test JWT verification with production keys
- [ ] Run security audit (SQL injection, XSS, CSRF tests)
- [ ] Set up monitoring and alerting

### Deployment

- [ ] Deploy database schema to Supabase production project
- [ ] Deploy backend with Supabase integration
- [ ] Deploy frontend with Supabase client
- [ ] Test authentication flow end-to-end
- [ ] Test portfolio creation/update/delete
- [ ] Test RLS policies in production
- [ ] Verify analytics event tracking
- [ ] Test shareable link generation
- [ ] Monitor error rates and latencies

### Post-Deployment

- [ ] Monitor Supabase dashboard for errors
- [ ] Check activity logs for unusual patterns
- [ ] Verify email delivery (welcome emails, password resets)
- [ ] Test OAuth flows (Google, GitHub)
- [ ] Set up automated database backups
- [ ] Document rollback procedures
- [ ] Create runbook for common issues
- [ ] Set up weekly usage reports

### Performance Monitoring

- [ ] Database query performance (P95 < 100ms)
- [ ] API endpoint latencies (P95 < 500ms)
- [ ] Authentication success rate (>99%)
- [ ] Error rate (<1%)
- [ ] Database CPU utilization (<70%)
- [ ] Connection pool saturation (<80%)

---

## Troubleshooting Guide

### Authentication Issues

**Problem: "Invalid JWT token" error**

Symptoms:
- Users see 401 Unauthorized errors
- API calls fail with "Could not validate credentials"

Solutions:
1. Verify `SUPABASE_JWT_SECRET` matches Supabase dashboard (Settings → API → JWT Secret)
2. Check token hasn't expired (JWT exp claim)
3. Ensure token is sent in `Authorization: Bearer <token>` header
4. Verify audience claim is "authenticated"

Debugging:
```bash
# Decode JWT to inspect claims
echo "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." | base64 -d
```

**Problem: "Token expired" errors**

Symptoms:
- Users logged out after 1 hour
- Frequent re-authentication required

Solutions:
1. Implement token refresh logic:
```typescript
// Auto-refresh tokens
supabase.auth.onAuthStateChange((event, session) => {
  if (event === 'TOKEN_REFRESHED') {
    console.log('Token refreshed successfully')
    // Update API calls with new token
  }
})
```

2. Increase token lifetime (Supabase Dashboard → Authentication → Settings):
   - Access token expiry: 3600 seconds (1 hour) - default
   - Refresh token expiry: 2592000 seconds (30 days) - default

**Problem: OAuth redirect not working**

Symptoms:
- Google/GitHub OAuth hangs after consent screen
- Redirect goes to wrong URL

Solutions:
1. Verify redirect URL in OAuth provider settings matches Supabase callback:
   - Google Cloud Console: `https://your-project.supabase.co/auth/v1/callback`
   - GitHub: `https://your-project.supabase.co/auth/v1/callback`
2. Ensure `emailRedirectTo` parameter is correct:
```typescript
await supabase.auth.signInWithOAuth({
  provider: 'google',
  options: {
    redirectTo: 'https://portfolionavigator.app/auth/callback',
  },
})
```

### Database Issues

**Problem: "Row-level security policy violation" error**

Symptoms:
- API returns empty results even though data exists
- INSERT/UPDATE/DELETE operations fail silently

Solutions:
1. Check RLS policies are correctly configured:
```sql
-- List all policies
SELECT * FROM pg_policies WHERE tablename = 'portfolios';
```

2. Test RLS as specific user:
```sql
-- Impersonate user
SET request.jwt.claims.sub = 'user-uuid-here';
SELECT * FROM portfolios; -- Should only see user's portfolios

-- Reset
RESET ALL;
```

3. Temporarily disable RLS for debugging (never in production):
```sql
ALTER TABLE portfolios DISABLE ROW LEVEL SECURITY;
```

**Problem: "Too many connections" error**

Symptoms:
- API intermittently fails with connection pool exhaustion
- Slow response times

Solutions:
1. Reduce connection pool size in backend:
```python
# backend/utils/supabase_client.py
supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    options={
        'db': {
            'pool_size': 10,  # Reduce from default 20
        }
    }
)
```

2. Upgrade Supabase tier to increase connection limit:
   - Free: 60 connections
   - Pro: 200 connections

**Problem: Slow query performance**

Symptoms:
- API endpoints timeout
- Dashboard takes >5 seconds to load

Solutions:
1. Check query plans:
```sql
EXPLAIN ANALYZE
SELECT * FROM portfolios WHERE user_id = 'uuid-here';
```

2. Add missing indexes:
```sql
CREATE INDEX idx_portfolios_user_created
  ON portfolios(user_id, created_at DESC);
```

3. Use Supabase dashboard → Database → Query Performance to identify slow queries

### API Issues

**Problem: CORS errors in browser console**

Symptoms:
- "Access-Control-Allow-Origin" error
- API calls fail from frontend

Solutions:
1. Verify CORS middleware configuration:
```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://portfolionavigator.app"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

2. Ensure frontend uses correct API URL (no trailing slash mismatches)

**Problem: Rate limiting too aggressive**

Symptoms:
- Legitimate users get 429 Too Many Requests errors
- Can't complete portfolio optimization

Solutions:
1. Increase rate limits for authenticated users:
```python
# backend/middleware/rate_limiting.py
class RateLimits:
    OPTIMIZE_AUTHENTICATED = "10/minute"  # Higher for logged-in users
    OPTIMIZE_ANONYMOUS = "3/minute"
```

2. Implement per-user rate limiting instead of per-IP

### Analytics Issues

**Problem: Events not showing in activity_log**

Symptoms:
- Empty analytics dashboard
- No event data in Supabase table

Solutions:
1. Check RLS policies allow INSERT:
```sql
-- Should exist
SELECT * FROM pg_policies
WHERE tablename = 'activity_log'
  AND cmd = 'INSERT';
```

2. Verify `track_event()` is being called:
```python
# Add debug logging
import logging
logging.info(f"Tracking event: {event_type}")
await track_event(...)
```

3. Check for errors in backend logs:
```bash
railway logs --tail 100
```

**Problem: Duplicate events in activity_log**

Symptoms:
- Same event logged multiple times
- Analytics counts are inflated

Solutions:
1. Add unique constraint to prevent duplicates:
```sql
CREATE UNIQUE INDEX idx_activity_log_dedup
  ON activity_log(user_id, event_type, created_at, event_metadata);
```

2. Debounce event tracking in frontend:
```typescript
import { debounce } from 'lodash'

const debouncedTrackEvent = debounce(trackEvent, 1000)
```

### Email Issues

**Problem: Users not receiving verification emails**

Symptoms:
- Signup succeeds but no email received
- Password reset emails never arrive

Solutions:
1. Check Supabase email rate limits (Free: 30,000/month)
2. Configure custom SMTP in Supabase Dashboard → Project Settings → Auth → SMTP Settings
3. Verify email templates are enabled: Dashboard → Authentication → Email Templates
4. Check spam folder

**Problem: Custom domain emails not working**

Symptoms:
- Emails sent from "noreply@supabase.co" instead of custom domain

Solutions:
1. Set up custom SMTP provider (SendGrid, Mailgun, AWS SES)
2. Configure in Supabase Dashboard → Project Settings → Auth → SMTP Settings:
   - Host: smtp.sendgrid.net
   - Port: 587
   - User: apikey
   - Password: <SendGrid API key>
   - Sender email: noreply@portfolionavigator.app

---

## Appendix: Quick Reference

### Supabase Client Snippets

```typescript
// Sign up
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'password123',
})

// Sign in
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password123',
})

// Sign out
await supabase.auth.signOut()

// Get current user
const { data: { user } } = await supabase.auth.getUser()

// Get current session
const { data: { session } } = await supabase.auth.getSession()

// Listen for auth changes
supabase.auth.onAuthStateChange((event, session) => {
  console.log(event, session)
})

// Insert data
const { data, error } = await supabase
  .from('portfolios')
  .insert({ name: 'My Portfolio', user_id: user.id })

// Query data
const { data, error } = await supabase
  .from('portfolios')
  .select('*')
  .eq('user_id', user.id)
  .order('created_at', { ascending: false })

// Update data
const { data, error } = await supabase
  .from('portfolios')
  .update({ name: 'Updated Name' })
  .eq('id', portfolioId)

// Delete data
const { data, error } = await supabase
  .from('portfolios')
  .delete()
  .eq('id', portfolioId)
```

### Useful SQL Queries

```sql
-- Get user portfolio count
SELECT user_id, COUNT(*) AS portfolio_count
FROM portfolios
GROUP BY user_id
ORDER BY portfolio_count DESC;

-- Get most popular strategies
SELECT strategy, COUNT(*) AS usage_count
FROM portfolios
GROUP BY strategy
ORDER BY usage_count DESC;

-- Get active users (logged in last 30 days)
SELECT COUNT(DISTINCT user_id) AS active_users
FROM activity_log
WHERE created_at >= NOW() - INTERVAL '30 days';

-- Get average portfolio size
SELECT AVG(array_length(tickers, 1)) AS avg_tickers
FROM portfolios;

-- Get top shared portfolios by views
SELECT id, name, view_count, share_token
FROM portfolios
WHERE is_public = true
ORDER BY view_count DESC
LIMIT 10;
```

### Environment Variables Reference

```bash
# Backend (.env)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... # SECRET!
SUPABASE_JWT_SECRET=your-jwt-secret-from-supabase

# Frontend (.env.local)
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Support Resources

- **Supabase Documentation**: https://supabase.com/docs
- **Supabase Discord**: https://discord.supabase.com
- **Supabase GitHub**: https://github.com/supabase/supabase
- **Stack Overflow**: Tag `supabase`
- **Community Forum**: https://github.com/supabase/supabase/discussions

---

## Summary

This Supabase Integration Plan provides a complete roadmap for adding production-grade authentication, persistent data storage, and analytics to Portfolio Navigator Wizard. By following this plan, you will:

1. ✅ **Eliminate Critical Security Vulnerability** (CVSS 9.8) with authentication
2. ✅ **Enable User Accounts** with email/password, OAuth, and magic links
3. ✅ **Persist Portfolio Data** in PostgreSQL with automatic backups
4. ✅ **Protect User Data** with Row-Level Security policies
5. ✅ **Track User Behavior** with comprehensive event analytics
6. ✅ **Scale Efficiently** from 0 to 50,000 users on free tier
7. ✅ **Save Development Time** by avoiding custom auth implementation
8. ✅ **Reduce Costs** by $20,000+ compared to custom solution

**Recommended Implementation Timeline:**
- Week 1: Supabase setup, database schema, backend integration
- Week 2: Frontend authentication UI, API updates, dashboard
- Week 3: Analytics implementation, monitoring, testing
- Total: 2-3 weeks to production-ready authentication

**Next Steps:**
1. Review this plan with the team
2. Create Supabase project and run database migrations
3. Start with Phase 1 (backend integration)
4. Follow the migration plan sequentially
5. Deploy to production with gradual rollout

For questions or support, refer to the Troubleshooting Guide or contact Supabase support via Discord/GitHub.
