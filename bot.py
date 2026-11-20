import asyncio
import json
import os
import sys
import logging
from datetime import datetime
import aiohttp
from database import (
    init_db, save_user, create_order, update_order_proof,
    mark_order_delivered, mark_order_rejected, get_order,
    get_user_orders, get_stats, get_all_user_ids
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("BharatBazaarBot")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load config
with open(os.path.join(BASE_DIR, "config.json"), "r") as f:
    CONFIG = json.load(f)

BOT_TOKEN = CONFIG["bot_token"]
ADMIN_ID = int(CONFIG["admin_id"])
UPI_ID = CONFIG["upi_id"]
BOT_NAME = CONFIG.get("bot_name", "Bharat Bazaar")
SUPPORT_USER = CONFIG.get("support_username", "Showstealer07")
FEEDBACK_CHANNEL = CONFIG.get("feedback_channel", "https://t.me/feedbecks")
DELIVERY_ESTIMATE = CONFIG.get("delivery_estimate", "Instant to 24-32 Hours")
QR_CODE_PATH = os.path.join(BASE_DIR, "assets", "qr_code.jpg")

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Load products
def load_products():
    with open(os.path.join(BASE_DIR, "products.json"), "r") as f:
        return json.load(f)

PRODUCTS = load_products()

# State memory
# user_states: {user_id: {"state": str, "order_id": str}}
# admin_states: {admin_id: {"state": str, "order_id": str}}
USER_STATES = {}
ADMIN_STATES = {}

class TelegramBot:
    def __init__(self):
        self.session = None

    async def init_session(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def api_call(self, method: str, data=None, files=None):
        await self.init_session()
        url = f"{API_URL}/{method}"
        try:
            if files:
                form = aiohttp.FormData()
                for k, v in (data or {}).items():
                    if isinstance(v, (dict, list)):
                        form.add_field(k, json.dumps(v))
                    else:
                        form.add_field(k, str(v))
                for file_key, file_val in files.items():
                    form.add_field(file_key, file_val[1], filename=file_val[0])
                async with self.session.post(url, data=form) as resp:
                    return await resp.json()
            else:
                async with self.session.post(url, json=data) as resp:
                    return await resp.json()
        except Exception as e:
            logger.error(f"API call error ({method}): {e}")
            return {"ok": False, "error": str(e)}

    async def send_message(self, chat_id, text, reply_markup=None, parse_mode="Markdown"):
        payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return await self.api_call("sendMessage", payload)

    async def send_photo(self, chat_id, photo_path_or_id, caption="", reply_markup=None, parse_mode="Markdown"):
        payload = {"chat_id": chat_id, "caption": caption, "parse_mode": parse_mode}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        # If it's a file path on disk
        if os.path.exists(str(photo_path_or_id)):
            with open(photo_path_or_id, "rb") as f:
                photo_bytes = f.read()
            files = {"photo": ("qr.jpg", photo_bytes)}
            return await self.api_call("sendPhoto", payload, files=files)
        else:
            # File ID
            payload["photo"] = photo_path_or_id
            return await self.api_call("sendPhoto", payload)

    async def answer_callback(self, callback_query_id, text=None, show_alert=False):
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
            payload["show_alert"] = show_alert
        return await self.api_call("answerCallbackQuery", payload)

    async def edit_message_text(self, chat_id, message_id, text, reply_markup=None, parse_mode="Markdown"):
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return await self.api_call("editMessageText", payload)

    async def delete_message(self, chat_id, message_id):
        return await self.api_call("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

    # UI Helpers
    def main_reply_keyboard(self):
        return {
            "keyboard": [
                [{"text": "🛍️ Products"}, {"text": "📦 My Orders"}],
                [{"text": "📞 Support"}, {"text": "🍀 Reviews & Proofs"}]
            ],
            "resize_keyboard": True,
            "persistent": True
        }

    def products_inline_keyboard(self):
        global PRODUCTS
        PRODUCTS = load_products()
        rows = []
        current_row = []
        
        for pid, pdata in PRODUCTS.items():
            btn_text = f"{pdata['name']} ₹{pdata['price']}"
            current_row.append({"text": btn_text, "callback_data": f"p:{pid}"})
            if len(current_row) == 2:
                rows.append(current_row)
                current_row = []
        if current_row:
            rows.append(current_row)
        return {"inline_keyboard": rows}

    # Handler Router
    async def handle_update(self, update):
        if "message" in update:
            await self.handle_message(update["message"])
        elif "callback_query" in update:
            await self.handle_callback(update["callback_query"])

    async def handle_message(self, msg):
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        username = msg["from"].get("username", "")
        first_name = msg["from"].get("first_name", "Friend")
        text = msg.get("text", "")

        # Save user to DB
        save_user(user_id, username, first_name)

        # Check Admin States first
        if user_id == ADMIN_ID and user_id in ADMIN_STATES:
            state_data = ADMIN_STATES[user_id]
            state = state_data.get("state")
            order_id = state_data.get("order_id")

            if state == "awaiting_delivery" and order_id:
                delivery_text = text or msg.get("caption", "")
                if not delivery_text:
                    await self.send_message(chat_id, "⚠️ Please send valid text/credentials to deliver.")
                    return
                
                # Fetch order
                order = get_order(order_id)
                if order:
                    mark_order_delivered(order_id, delivery_text)
                    del ADMIN_STATES[user_id]

                    # Notify buyer
                    buyer_text = (
                        f"🎉 **Order #{order_id} Delivered!**\n\n"
                        f"🛍 **Product:** {order['product_name']}\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"📦 **Your Access / Credentials:**\n"
                        f"```\n{delivery_text}\n```\n"
                        f"━━━━━━━━━━━━━━━━━━\n\n"
                        f"❤️ Thank you for choosing *{BOT_NAME}*!\n"
                        f"🍀 Drop your review in {FEEDBACK_CHANNEL}"
                    )
                    await self.send_message(order["user_id"], buyer_text)
                    await self.send_message(chat_id, f"✅ **Order #{order_id} successfully delivered** to @{order['username'] or order['user_id']}!")
                return

            elif state == "awaiting_broadcast":
                del ADMIN_STATES[user_id]
                uids = get_all_user_ids()
                sent = 0
                for uid in uids:
                    try:
                        await self.send_message(uid, f"📢 **Announcement from {BOT_NAME}:**\n\n{text}")
                        sent += 1
                        await asyncio.sleep(0.05)
                    except Exception:
                        pass
                await self.send_message(chat_id, f"✅ Broadcast sent to {sent}/{len(uids)} users!")
                return

        # Check User States (Waiting for payment screenshot or UTR)
        if user_id in USER_STATES:
            ustate = USER_STATES[user_id]
            order_id = ustate.get("order_id")

            if "photo" in msg:
                # User sent screenshot
                photo = msg["photo"][-1]  # Highest resolution
                file_id = photo["file_id"]
                update_order_proof(order_id, file_id=file_id)
                del USER_STATES[user_id]

                order = get_order(order_id)
                # Confirm to buyer
                await self.send_message(
                    chat_id,
                    f"✅ **Payment Screenshot Received!**\n\n"
                    f"📦 Order: `#{order_id}`\n"
                    f"🛍 Product: **{order['product_name']}**\n"
                    f"💰 Amount: **₹{order['amount']}**\n\n"
                    f"🔍 Our team is verifying your payment.\n"
                    f"⚡ Delivery within **{DELIVERY_ESTIMATE}**.",
                    reply_markup=self.main_reply_keyboard()
                )

                # Send alert to Admin
                admin_caption = (
                    f"🔔 **NEW PAYMENT PROOF RECEIVED!**\n\n"
                    f"📦 **Order ID:** `#{order_id}`\n"
                    f"👤 **Buyer:** @{username} (ID: `{user_id}`)\n"
                    f"🛍 **Product:** {order['product_name']}\n"
                    f"💰 **Amount:** ₹{order['amount']}\n"
                    f"🕒 **Time:** {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\n"
                    f"Verify payment in your Paytm/Bank app and select action:"
                )
                admin_kb = {
                    "inline_keyboard": [
                        [
                            {"text": "✅ Approve & Deliver", "callback_data": f"adm_app:{order_id}"},
                            {"text": "❌ Reject Order", "callback_data": f"adm_rej:{order_id}"}
                        ]
                    ]
                }
                await self.send_photo(ADMIN_ID, file_id, caption=admin_caption, reply_markup=admin_kb)
                return

            elif text and not text.startswith("/"):
                # Treat text as UTR number
                update_order_proof(order_id, utr=text)
                del USER_STATES[user_id]

                order = get_order(order_id)
                await self.send_message(
                    chat_id,
                    f"✅ **UTR / Transaction ID Received:** `{text}`\n\n"
                    f"📦 Order: `#{order_id}`\n"
                    f"🔍 Verification in progress. Delivery in **{DELIVERY_ESTIMATE}**.",
                    reply_markup=self.main_reply_keyboard()
                )

                # Notify Admin
                admin_msg = (
                    f"🔔 **NEW ORDER UTR RECEIVED!**\n\n"
                    f"📦 **Order ID:** `#{order_id}`\n"
                    f"👤 **Buyer:** @{username} (ID: `{user_id}`)\n"
                    f"🛍 **Product:** {order['product_name']}\n"
                    f"💰 **Amount:** ₹{order['amount']}\n"
                    f"🔢 **UTR / Ref:** `{text}`\n\n"
                    f"Verify payment and select action:"
                )
                admin_kb = {
                    "inline_keyboard": [
                        [
                            {"text": "✅ Approve & Deliver", "callback_data": f"adm_app:{order_id}"},
                            {"text": "❌ Reject Order", "callback_data": f"adm_rej:{order_id}"}
                        ]
                    ]
                }
                await self.send_message(ADMIN_ID, admin_msg, reply_markup=admin_kb)
                return

        # Commands & Menu handling
        if text.startswith("/start"):
            welcome_text = (
                f"👋 **Welcome to {BOT_NAME}!**\n\n"
                f"Hello {first_name}!\n\n"
                f"🛍 Browse our premium services and choose your plan.\n"
                f"💳 Pay securely via Verified Merchant UPI Gateways.\n"
                f"⚡ **Get instant delivery within {DELIVERY_ESTIMATE}.**\n"
                f"🍀 **Trust issues? Visit {FEEDBACK_CHANNEL}**\n\n"
                f"👇 Click on **🛍️ Products** to start shopping!"
            )
            await self.send_message(chat_id, welcome_text, reply_markup=self.main_reply_keyboard())
            return

        elif text in ["🛍️ Products", "/products"]:
            shop_text = f"🛍 **{BOT_NAME} Shop**\n\nSelect a product below to view details and order:"
            await self.send_message(chat_id, shop_text, reply_markup=self.products_inline_keyboard())
            return

        elif text in ["📦 My Orders", "/orders"]:
            orders = get_user_orders(user_id)
            if not orders:
                await self.send_message(
                    chat_id,
                    "📦 **You don't have any orders yet.**\n\nClick **🛍️ Products** to place your first order!",
                    reply_markup=self.main_reply_keyboard()
                )
                return

            res = ["📦 **Your Recent Orders:**\n"]
            for o in orders:
                status_emoji = {
                    "WAITING_PAYMENT": "⏳ Awaiting Payment",
                    "PENDING_VERIFICATION": "🔍 Verifying Payment",
                    "DELIVERED": "✅ Delivered",
                    "REJECTED": "❌ Rejected"
                }.get(o["status"], o["status"])

                res.append(
                    f"• **Order:** `#{o['order_id']}`\n"
                    f"  **Product:** {o['product_name']} (₹{o['amount']})\n"
                    f"  **Status:** {status_emoji}\n"
                    f"  **Date:** {o['created_at'][:16]}"
                )
                if o["status"] == "DELIVERED" and o["delivery_data"]:
                    res.append(f"  🔑 **Delivery:**\n```\n{o['delivery_data']}\n```")
                res.append("━━━━━━━━━━━━━━━━━━")

            await self.send_message(chat_id, "\n".join(res), reply_markup=self.main_reply_keyboard())
            return

        elif text in ["📞 Support", "/support"]:
            support_text = (
                f"📞 **Customer Support**\n\n"
                f"If you have any questions, need payment verification, or want custom packages:\n\n"
                f"👤 **Admin Support:** @{SUPPORT_USER}\n"
                f"🍀 **Vouches & Proofs:** {FEEDBACK_CHANNEL}\n\n"
                f"We are active 24/7 to help you!"
            )
            await self.send_message(chat_id, support_text, reply_markup=self.main_reply_keyboard())
            return

        elif text in ["🍀 Reviews & Proofs", "/reviews"]:
            await self.send_message(
                chat_id,
                f"🍀 **Customer Reviews & Proofs:**\n\nJoin our feedback channel to see all customer deliveries:\n👉 {FEEDBACK_CHANNEL}",
                reply_markup=self.main_reply_keyboard()
            )
            return

        elif text in ["/admin", "Admin"] and user_id == ADMIN_ID:
            stats = get_stats()
            adm_text = (
                f"👑 **{BOT_NAME} - Admin Dashboard**\n\n"
                f"👥 **Total Users:** {stats['total_users']}\n"
                f"📦 **Total Orders:** {stats['total_orders']}\n"
                f"✅ **Delivered Orders:** {stats['delivered_count']}\n"
                f"💰 **Total Revenue:** ₹{stats['total_revenue']}\n"
                f"⏳ **Pending Verification:** {stats['pending_orders']}\n"
            )
            adm_kb = {
                "inline_keyboard": [
                    [{"text": "📢 Broadcast Message", "callback_data": "adm_broadcast"}],
                    [{"text": "🔄 Refresh Stats", "callback_data": "adm_refresh"}]
                ]
            }
            await self.send_message(chat_id, adm_text, reply_markup=adm_kb)
            return

    async def handle_callback(self, cb):
        global PRODUCTS
        PRODUCTS = load_products()
        cb_id = cb["id"]
        chat_id = cb["message"]["chat"]["id"]
        message_id = cb["message"]["message_id"]
        user_id = cb["from"]["id"]
        username = cb["from"].get("username", "")
        data = cb.get("data", "")

        # Product details
        if data.startswith("p:"):
            pid = data.split(":", 1)[1]
            prod = PRODUCTS.get(pid)
            if not prod:
                await self.answer_callback(cb_id, "Product not found!", show_alert=True)
                return

            text = (
                f"🛍 **{prod['name']}**\n\n"
                f"{prod['description']}\n\n"
                f"💰 **Price:** ₹{prod['price']}\n"
                f"📦 **Delivery Type:** {prod.get('delivery_type', 'Credentials')}\n"
                f"⚡ **Estimated Delivery:** {DELIVERY_ESTIMATE}\n"
            )
            kb = {
                "inline_keyboard": [
                    [{"text": f"💳 Buy Now ₹{prod['price']}", "callback_data": f"buy:{pid}"}],
                    [{"text": "🔙 Back to Products", "callback_data": "back_to_shop"}]
                ]
            }
            await self.answer_callback(cb_id)
            await self.edit_message_text(chat_id, message_id, text, reply_markup=kb)
            return

        # Back to shop
        elif data == "back_to_shop":
            await self.answer_callback(cb_id)
            await self.edit_message_text(
                chat_id, message_id,
                f"🛍 **{BOT_NAME} Shop**\n\nSelect a product below:",
                reply_markup=self.products_inline_keyboard()
            )
            return

        # Buy product
        elif data.startswith("buy:"):
            pid = data.split(":", 1)[1]
            prod = PRODUCTS.get(pid)
            if not prod:
                await self.answer_callback(cb_id, "Product expired!", show_alert=True)
                return

            await self.answer_callback(cb_id)
            # Create order
            order_id = create_order(user_id, username, pid, prod["name"], prod["price"])
            USER_STATES[user_id] = {"state": "awaiting_payment_proof", "order_id": order_id}

            caption = (
                f"🛍 **Order Created: `#{order_id}`**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📦 **Product:** {prod['name']}\n"
                f"💰 **Payable Amount:** **₹{prod['price']}**\n\n"
                f"💳 **Paytm / Any UPI App:**\n"
                f"UPI ID: `{UPI_ID}` *(Tap to copy)*\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📸 **पेमेंट करने के बाद:**\n"
                f"1. ऊपर दिए गए **QR कोड** को स्कैन करके या **UPI ID** पर ₹{prod['price']} भेजें।\n"
                f"2. पेमेंट का **स्क्रीनशॉट (Screenshot)** या **12-digit UTR नंबर** इसी चैट में भेजें।\n\n"
                f"⚡ स्क्रीनशॉट आते ही वेरिफिकेशन और डिलीवरी शुरू हो जाएगी!"
            )
            kb = {
                "inline_keyboard": [
                    [{"text": "❌ Cancel Order", "callback_data": f"cancel_order:{order_id}"}]
                ]
            }
            # Send Paytm QR Code image
            await self.send_photo(chat_id, QR_CODE_PATH, caption=caption, reply_markup=kb)
            return

        # Cancel order
        elif data.startswith("cancel_order:"):
            order_id = data.split(":", 1)[1]
            if user_id in USER_STATES:
                del USER_STATES[user_id]
            mark_order_rejected(order_id, reason="Cancelled by user")
            await self.answer_callback(cb_id, "Order cancelled.", show_alert=True)
            await self.send_message(chat_id, f"❌ Order `#{order_id}` cancelled.\nClick **🛍️ Products** anytime to browse.", reply_markup=self.main_reply_keyboard())
            return

        # Admin Actions
        if user_id == ADMIN_ID:
            if data.startswith("adm_app:"):
                order_id = data.split(":", 1)[1]
                order = get_order(order_id)
                if not order:
                    await self.answer_callback(cb_id, "Order not found!", show_alert=True)
                    return
                
                ADMIN_STATES[ADMIN_ID] = {"state": "awaiting_delivery", "order_id": order_id}
                await self.answer_callback(cb_id)
                await self.send_message(
                    ADMIN_ID,
                    f"✍️ **Ready to Deliver #{order_id} ({order['product_name']})**\n\n"
                    f"Now type or paste the **login credentials / key / invite link** in this chat.\n"
                    f"It will be forwarded directly to the buyer (@{order['username'] or order['user_id']})."
                )
                return

            elif data.startswith("adm_rej:"):
                order_id = data.split(":", 1)[1]
                order = get_order(order_id)
                if order:
                    mark_order_rejected(order_id, reason="Invalid payment proof")
                    await self.answer_callback(cb_id, f"Order #{order_id} rejected.", show_alert=True)
                    await self.send_message(
                        order["user_id"],
                        f"❌ **Order #{order_id} Rejected**\n\n"
                        f"Your payment proof could not be verified.\n"
                        f"If you already paid, please reach out to Support: @{SUPPORT_USER}"
                    )
                    await self.send_message(ADMIN_ID, f"❌ Order #{order_id} has been marked as rejected.")
                return

            elif data == "adm_broadcast":
                ADMIN_STATES[ADMIN_ID] = {"state": "awaiting_broadcast"}
                await self.answer_callback(cb_id)
                await self.send_message(
                    ADMIN_ID,
                    "📢 **Broadcast Mode Active**\n\nPlease send the message you want to broadcast to all bot users:"
                )
                return

            elif data == "adm_refresh":
                stats = get_stats()
                adm_text = (
                    f"👑 **{BOT_NAME} - Admin Dashboard**\n\n"
                    f"👥 **Total Users:** {stats['total_users']}\n"
                    f"📦 **Total Orders:** {stats['total_orders']}\n"
                    f"✅ **Delivered Orders:** {stats['delivered_count']}\n"
                    f"💰 **Total Revenue:** ₹{stats['total_revenue']}\n"
                    f"⏳ **Pending Verification:** {stats['pending_orders']}\n"
                )
                adm_kb = {
                    "inline_keyboard": [
                        [{"text": "📢 Broadcast Message", "callback_data": "adm_broadcast"}],
                        [{"text": "🔄 Refresh Stats", "callback_data": "adm_refresh"}]
                    ]
                }
                await self.answer_callback(cb_id, "Refreshed!")
                await self.edit_message_text(chat_id, message_id, adm_text, reply_markup=adm_kb)
                return

    # Polling Loop
    async def run(self):
        init_db()
        await self.init_session()
        logger.info(f"🚀 Starting {BOT_NAME} (@BharatBazaarBot)...")
        
        offset = 0
        # Delete any pending webhook to use polling
        await self.api_call("deleteWebhook", {"drop_pending_updates": False})
        
        # Test getMe
        me = await self.api_call("getMe")
        if not me.get("ok"):
            logger.error(f"Failed to authenticate bot token: {me}")
            return
        
        logger.info(f"Bot connected: @{me['result']['username']} (ID: {me['result']['id']})")
        
        while True:
            try:
                updates = await self.api_call("getUpdates", {"offset": offset, "timeout": 25})
                if updates.get("ok"):
                    for u in updates["result"]:
                        offset = u["update_id"] + 1
                        asyncio.create_task(self.handle_update(u))
                else:
                    logger.warning(f"getUpdates error: {updates}")
                    await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Polling loop exception: {e}")
                await asyncio.sleep(3)

if __name__ == "__main__":
    bot = TelegramBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
