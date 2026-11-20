import asyncio
import json
import os
import random
import logging
from telethon import TelegramClient
from telethon.errors import PeerFloodError, UserPrivacyRestrictedError, FloodWaitError
from telethon.tl.types import User

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MassBroadcaster")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SENT_FILE = os.path.join(BASE_DIR, "data", "sent_users.json")
LOG_FILE = os.path.join(BASE_DIR, "mass_broadcast.log")

# Setup file handler
fh = logging.FileHandler(LOG_FILE)
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(fh)

API_ID = 28988826
API_HASH = "90a79ce6dfb7aee81ba7ef0d60a640d7"
SESSION_PATH = "/data/user/0/ai.antigem/files/home/projects/telegram_downloader/user_session"

PROMO_MESSAGE = """🎬 **All Web Series, All Reality Shows & Movies Available!** 🍿

⚡ **Premium OTT & Subscriptions at Cheapest Rates:**
• Prime Video (₹49) | Netflix 4K (₹179)
• YouTube Premium (₹59) | Spotify 3 Months (₹59)
• JioHotstar 4K (₹60) | Canva Pro (₹49)
• Windows & Office Activations (₹69+)

✅ 100% Verified & Instant Delivery!
👉 **Start Bot Now:** @BharatBazaarBot"""

def load_sent_users():
    if os.path.exists(SENT_FILE):
        try:
            with open(SENT_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_sent_user(uid: int):
    sent = load_sent_users()
    sent.add(uid)
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent), f, indent=2)

async def main():
    sent_set = load_sent_users()
    logger.info(f"Loaded {len(sent_set)} already-messaged users.")

    async with TelegramClient(SESSION_PATH, API_ID, API_HASH) as client:
        me = await client.get_me()
        logger.info(f"Starting broadcast as @{me.username} ({me.id})")

        success_count = 0
        skipped_count = 0

        async for d in client.iter_dialogs():
            entity = d.entity
            if isinstance(entity, User) and not entity.bot and not entity.is_self:
                uid = entity.id
                if uid in [777000, 454000, 4245000]:
                    continue

                if uid in sent_set:
                    continue

                name = d.name or str(uid)
                try:
                    logger.info(f"Sending to: {name} (ID: {uid})...")
                    await client.send_message(entity, PROMO_MESSAGE)
                    save_sent_user(uid)
                    sent_set.add(uid)
                    success_count += 1
                    logger.info(f"✅ [{success_count} sent this session | Total: {len(sent_set)}] Sent to {name}")

                    # Anti-ban safe jitter delay: 15-20 seconds
                    delay = random.uniform(15.0, 20.0)
                    logger.info(f"Waiting {delay:.1f}s before next contact...")
                    await asyncio.sleep(delay)

                except PeerFloodError:
                    logger.error("🚨 Telegram PeerFlood limit reached! Telegram has paused new DMs for this account.")
                    logger.error("🛑 Stopping process immediately to prevent account suspension/ban.")
                    break
                except FloodWaitError as fe:
                    logger.warning(f"⏳ FloodWait of {fe.seconds}s encountered.")
                    if fe.seconds > 60:
                        logger.error("FloodWait is too long. Stopping for now.")
                        break
                    await asyncio.sleep(fe.seconds + 2)
                except UserPrivacyRestrictedError:
                    logger.warning(f"🔒 {name} has privacy restrictions enabled. Skipped.")
                    skipped_count += 1
                except Exception as ex:
                    logger.warning(f"⚠️ Could not send to {name}: {ex}")
                    skipped_count += 1

        logger.info(f"🏁 Broadcast session finished. Sent: {success_count}, Skipped/Error: {skipped_count}, Total reached so far: {len(sent_set)}")

if __name__ == "__main__":
    asyncio.run(main())
