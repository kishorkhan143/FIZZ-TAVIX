# TAVIX GUARD — Email Authentication Setup Guide

## Overview

This guide explains how to set up and use the new email-based authentication system for TAVIX GUARD using Resend for transactional emails and JWT for session management.

---

## Architecture

### Frontend Flow

1. **Login Page** (`/login`)
   - User enters email address
   - Clicks "Send Verification Link"
   - Email sent via backend to Resend
   - Success message shown

2. **Verification Page** (`/verify-email`)
   - User receives email with verification link
   - Clicks link (contains token)
   - Page auto-verifies and issues JWT
   - Redirects to dashboard

3. **Dashboard Protection**
   - Protected by `ProtectedRoute` wrapper
   - Requires valid JWT token
   - Unauthenticated users redirected to login
   - Token persisted in localStorage

### Backend Flow

1. **POST /api/auth/request-verification**
   - Accept email
   - Validate email format
   - Generate verification token (15-min expiry)
   - Send email via Resend
   - Store user in database

2. **GET /api/auth/verify-email**
   - Accept token as query param
   - Validate token expiry
   - Mark user as verified
   - Issue JWT token (30-day expiry)
   - Return JWT to frontend

3. **GET /api/auth/me**
   - Require JWT in Authorization header
   - Return authenticated user info
   - Protected route example

4. **POST /api/auth/logout**
   - Optional endpoint
   - Frontend clears JWT from localStorage

---

## Setup Instructions

### Backend Setup

#### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

New packages added:
- `resend==1.4.0` — Email service
- `PyJWT==2.8.1` — JWT token management
- `email-validator==2.1.0` — Email validation

#### 2. Create `.env.local` File

```bash
# Copy the template
cp .env.example .env.local
```

Edit `.env.local`:

```env
# Resend Email Configuration
RESEND_API_KEY=re_your_api_key_here
RESEND_FROM_EMAIL=noreply@yourdomain.com

# JWT Configuration (change to a strong secret)
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production

# Frontend URL (used in verification email links)
FRONTEND_URL=http://localhost:5173
```

**Getting a Resend API Key:**
1. Go to https://resend.com
2. Create an account or sign in
3. Navigate to API Keys
4. Create a new API key
5. Copy the key and paste into `.env.local`
6. Verify your sender domain with Resend (or use their sandbox domain)

#### 3. Initialize Database

The `User` model is already added to `models.py`. When you run the backend:

```bash
python main.py
```

The database will auto-initialize with the new `users` table.

#### 4. Run Backend

```bash
python main.py
```

Backend starts on `http://localhost:8000`

**Mock Email Mode:** If `RESEND_API_KEY` is not set, emails are logged to console.

---

### Frontend Setup

#### 1. Install Dependencies

```bash
cd frontend
npm install
```

New packages added:
- `react-router-dom==^6.20.0` — Client-side routing

#### 2. Create `.env.local` File

```bash
# Copy or create .env.local in frontend directory
cat > .env.local << EOF
VITE_BACKEND_URL=http://localhost:8000
EOF
```

#### 3. Run Frontend

```bash
npm run dev
```

Frontend starts on `http://localhost:5173`

---

## File Structure

### Backend Files Added

```
backend/
├── auth_service.py          # Email, JWT, token generation utilities
├── auth_router.py           # Authentication endpoints
├── models.py                # Updated with User model
├── schemas.py               # Updated with auth schemas
├── main.py                  # Updated to include auth router
├── requirements.txt         # Updated with new dependencies
├── .env.example             # Environment template
└── .env.local               # Your local config (not committed)
```

### Frontend Files Added

```
frontend/src/
├── App.jsx                  # Main router (updated)
├── Dashboard.jsx            # Dashboard layout (NEW)
├── useAuth.js               # Auth hook (NEW)
├── main.jsx                 # Updated with Router
├── pages/
│   ├── LoginPage.jsx        # Email entry (NEW)
│   └── VerifyEmailPage.jsx  # Email verification (NEW)
├── components/
│   └── ProtectedRoute.jsx   # Route guard (NEW)
└── styles/
    ├── LoginPage.css        # Login page styles (NEW)
    └── VerifyEmailPage.css  # Verification page styles (NEW)
```

---

## Testing the Authentication Flow

### Scenario 1: Complete Flow (with Resend)

1. **Start Backend:**
   ```bash
   cd backend
   python main.py
   ```

2. **Start Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Open http://localhost:5173**
   - Redirected to `/login` (not authenticated)

4. **Enter Email and Send Verification**
   - Email: `test@example.com`
   - Click "Send Verification Link"
   - Check email inbox

5. **Click Verification Link**
   - Email contains link like: `http://localhost:5173/verify-email?token=abc123...`
   - Click the link
   - Page shows "Email verified successfully!"
   - Redirects to dashboard after 3 seconds

6. **Dashboard Loads**
   - JWT token stored in localStorage
   - Dashboard displays normally
   - Logout button in sidebar

7. **Test Logout**
   - Click "Logout" in sidebar
   - Redirected to `/login`
   - Token cleared from localStorage

8. **Refresh Page**
   - Redirected to login (no token)
   - Login again to restore access

### Scenario 2: Mock Email Mode (for testing without Resend)

If you don't have a Resend API key:

1. Leave `RESEND_API_KEY` empty in `.env.local`
2. Backend logs verification emails to console

Example output:
```
[MOCK EMAIL] Verification link for test@example.com:
[MOCK EMAIL] Click here: http://localhost:5173/verify-email?token=abc123...
[MOCK EMAIL] Token expires in 15 minutes
```

Copy the link from console and paste in browser.

---

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(256) UNIQUE NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(512),
    verification_token_expires_at DATETIME,
    jwt_secret VARCHAR(512),
    created_at DATETIME NOT NULL,
    verified_at DATETIME,
    UNIQUE(email),
    INDEX(email),
    INDEX(verification_token)
)
```

---

## API Endpoints

### POST /api/auth/request-verification

Send verification email.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Verification email sent to user@example.com. Please check your inbox."
}
```

**Error (400 Bad Request):**
```json
{
  "detail": "Invalid email format: ..."
}
```

---

### GET /api/auth/verify-email?token=abc123

Verify email and issue JWT.

**Query Params:**
- `token` (required) — Verification token from email link

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Email verified successfully! Welcome, user@example.com",
  "jwt_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "is_verified": true
  }
}
```

**Error (400 Bad Request):**
```json
{
  "detail": "Verification token has expired. Please request a new one."
}
```

---

### GET /api/auth/me

Get current user info (requires JWT).

**Headers:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "is_verified": true,
  "created_at": "2025-01-15T10:30:00Z",
  "verified_at": "2025-01-15T10:31:00Z"
}
```

**Error (401 Unauthorized):**
```json
{
  "detail": "Invalid or expired token"
}
```

---

### POST /api/auth/logout

Logout endpoint (optional).

**Headers:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Logged out successfully. Clear your token from storage."
}
```

---

## Security Considerations

### Verification Tokens
- 15-minute expiry
- Single-use (cleared after verification)
- Stored in database

### JWT Tokens
- 30-day expiry
- Signed with `JWT_SECRET_KEY`
- Stored in localStorage (frontend)
- Included in `Authorization: Bearer <token>` header

### Recommendations for Production

1. **Change JWT_SECRET_KEY**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Use HTTPS Only**
   - Set `secure` flag on JWT cookies
   - Verify `FRONTEND_URL` uses HTTPS

3. **CORS Configuration**
   - Tighten `allow_origins` in `main.py`
   - Currently set to `["*"]` for development

4. **Database**
   - Use PostgreSQL in production (not SQLite)
   - Add database backups and replication

5. **Email Domain**
   - Verify sender domain with Resend
   - Use custom domain for professional emails

6. **Rate Limiting**
   - Add rate limit to `/api/auth/request-verification`
   - Prevent email spam

---

## Troubleshooting

### Issue: "Verification token is missing from the URL"

**Cause:** URL doesn't have `?token=...` query param

**Solution:**
- Check email link format: `http://localhost:5173/verify-email?token=abc123`
- Make sure `FRONTEND_URL` is correct in `.env.local`

---

### Issue: "Verification token has expired"

**Cause:** Token is older than 15 minutes

**Solution:**
- Request a new verification email
- Tokens expire after 15 minutes for security

---

### Issue: Email not received

**Cause 1:** RESEND_API_KEY not set

**Solution:**
- Check `.env.local` has `RESEND_API_KEY=re_...`
- Check backend logs for mock email output

**Cause 2:** Sender domain not verified with Resend

**Solution:**
- Log into Resend dashboard
- Verify your sender domain
- Or use Resend sandbox domain

**Cause 3:** Email went to spam

**Solution:**
- Check spam/junk folder
- Resend is reputable, but check email provider settings

---

### Issue: "Invalid or expired token" on dashboard

**Cause:** JWT token expired

**Solution:**
- Token expires after 30 days
- Log in again to get new token
- Token is auto-checked on app load

---

### Issue: Stuck on loading screen

**Cause:** Frontend can't reach backend

**Solution:**
- Check backend is running: `http://localhost:8000`
- Check `VITE_BACKEND_URL` in `.env.local`
- Check browser console for CORS errors

---

## Next Steps

1. **Test the complete flow** following Scenario 1 above
2. **Configure Resend** with your sender domain
3. **Deploy to production** with environment variables
4. **Add multi-user support** (currently any verified email can access)
5. **Add password-based login** (optional enhancement)

---

## Files Modified/Created

### Backend
- ✅ `models.py` — Added `User` model
- ✅ `schemas.py` — Added auth request/response schemas
- ✅ `auth_service.py` — Email, JWT, token utilities (NEW)
- ✅ `auth_router.py` — Authentication endpoints (NEW)
- ✅ `main.py` — Integrated auth router
- ✅ `requirements.txt` — Added dependencies
- ✅ `.env.example` — Configuration template (NEW)

### Frontend
- ✅ `App.jsx` — Main router (updated)
- ✅ `Dashboard.jsx` — Dashboard layout (NEW)
- ✅ `useAuth.js` — Auth hook (NEW)
- ✅ `main.jsx` — Added Router (updated)
- ✅ `pages/LoginPage.jsx` — Login form (NEW)
- ✅ `pages/VerifyEmailPage.jsx` — Email verification (NEW)
- ✅ `components/ProtectedRoute.jsx` — Route guard (NEW)
- ✅ `styles/LoginPage.css` — Login styles (NEW)
- ✅ `styles/VerifyEmailPage.css` — Verification styles (NEW)
- ✅ `package.json` — Added react-router-dom (updated)
- ✅ `.env.local` — Frontend config (NEW)

---

## Implementation Status

- ✅ **Task 1:** User model added to database
- ✅ **Task 2:** Resend integration with auth_service.py
- ✅ **Task 3:** Authentication endpoints (/api/auth/*)
- ✅ **Task 4:** Login and Verify pages
- ✅ **Task 5:** JWT token management and auth hook
- ✅ **Task 6:** JWT middleware in backend (ready to apply)
- ✅ **Task 7:** Route protection with ProtectedRoute
- ✅ **Task 8:** Ready for full integration testing

**Next:** Run the application and test the complete authentication flow!
