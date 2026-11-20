import asyncio
import random
import logging
from telethon import TelegramClient
from telethon.errors import PeerFloodError, UserPrivacyRestrictedError, FloodWaitError
from telethon.tl.types import User, Channel, Chat

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PromoShare")

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

# Channels & Groups to post
TARGET_CHATS = [
    4438511710,  # Bigg Boss 20 Episodes Channel
    2933532561,  # Bigg Boss Season 20 Group
    4446744274   # Paid group
]

MAX_USERS = 20

async def main():
    async with TelegramClient(SESSION_PATH, API_ID, API_HASH) as client:
        me = await client.get_me()
        logger.info(f"Logged in as: {me.first_name} (@{me.username})")

        # 1. Post to Channels and Groups (Option 2)
        logger.info("=== STEP 1: Posting to Channels & Groups ===")
        for cid in TARGET_CHATS:
            try:
                entity = await client.get_entity(cid)
                title = getattr(entity, 'title', str(cid))
                logger.info(f"Sending to Group/Channel: {title}...")
                await client.send_message(entity, PROMO_MESSAGE)
                logger.info(f"✅ Successfully posted to: {title}")
                await asyncio.sleep(5)
            except Exception as e:
                logger.warning(f"⚠️ Could not post to {cid}: {e}")

        # 2. Post to Top 20 Recent Personal Users (Option 1)
        logger.info(f"=== STEP 2: Sending to Top {MAX_USERS} Personal Contacts ===")
        sent_users = 0
        failed_users = 0

        async for d in client.iter_dialogs():
            if sent_users >= MAX_USERS:
                break
            
            entity = d.entity
            if isinstance(entity, User) and not entity.bot and not entity.is_self:
                if entity.id in [777000, 454000, 4245000]:
                    continue
                
                name = d.name or str(entity.id)
                try:
                    logger.info(f"[{sent_users+1}/{MAX_USERS}] Sending DM to {name} (@{entity.username})...")
                    await client.send_message(entity, PROMO_MESSAGE)
                    sent_users += 1
                    logger.info(f"✅ Sent to {name}")
                    
                    # Safe natural jitter delay (12-16 seconds)
                    delay = random.uniform(12.0, 16.0)
                    logger.info(f"Sleeping {delay:.1f}s for safety...")
                    await asyncio.sleep(delay)

                except PeerFloodError:
                    logger.error("🚨 Telegram PeerFlood limit reached! Stopping immediately to protect account.")
                    break
                except UserPrivacyRestrictedError:
                    logger.warning(f"🔒 {name} has privacy restrictions, skipped.")
                    failed_users += 1
                except FloodWaitError as fe:
                    logger.error(f"⏳ FloodWait of {fe.seconds}s, stopping.")
                    break
                except Exception as ex:
                    logger.warning(f"⚠️ Error sending to {name}: {ex}")
                    failed_users += 1

        logger.info(f"🎉 Promo task finished! Total DMs sent: {sent_users}, Errors/Skipped: {failed_users}")

if __name__ == "__main__":
    asyncio.run(main())
