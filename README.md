# 🛍️ Bharat Bazaar Bot (@BharatBazaarBot)

A production-ready Telegram Store & Digital Goods Bazaar Bot with automated catalog, UPI QR Code payments, Admin order approval & delivery system, order history, and broadcast capabilities.

---

## 🚀 Quick Control (Termux / Linux)
```bash
# Start bot in background
cd ~/projects/bharat-bazaar-bot && ./start.sh

# Check bot status & live logs
./status.sh

# Stop bot
./stop.sh
```

---

## ⚙️ Features
1. **Interactive Product Grid**:
   - Prime Video, Netflix 4K, YouTube Premium, Canva Pro, Hotstar, Music apps, Windows/Office activations, etc.
   - Prices & details editable in `products.json` anytime.
2. **Dynamic UPI & QR Checkout**:
   - Shows user's Paytm QR Code directly on checkout.
   - Tap-to-copy UPI ID (`paytmqr10u9hhjq35@paytm`).
3. **Automated Admin Order Alert**:
   - Customer submits payment screenshot or UTR number.
   - Admin receives immediate alert with photo, buyer details, and `[Approve & Deliver]` / `[Reject]` buttons.
4. **Instant In-Bot Delivery**:
   - Admin clicks `Approve & Deliver`, types the credentials/keys, and bot immediately delivers to the buyer!
5. **Customer Order Tracking (`📦 My Orders`)**:
   - Buyer can view their past orders, status, and delivered credentials anytime.
6. **Admin Panel (`/admin`)**:
   - Live analytics (Total Users, Total Orders, Revenue, Pending approvals).
   - Instant broadcast message to all users.

---

## 🌐 24×7 Lifetime Free Cloud Hosting (Never Sleep)

### Option 1: Render.com (Recommended - 100% Free)
1. Upload this folder (`~/projects/bharat-bazaar-bot`) to a private GitHub repository.
2. Go to [Render.com](https://render.com) and create a **New Background Worker** (or Web Service).
3. Connect your GitHub repository.
4. Settings:
   - **Environment:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python3 bot.py`
5. Click **Deploy** — It runs 24×7 forever for ₹0!

### Option 2: Koyeb.com (100% Free Docker / Python)
1. Go to [Koyeb.com](https://koyeb.com) -> Create App -> GitHub.
2. Build command: `pip install -r requirements.txt`, Run: `python3 bot.py`.
3. Deploy!
