import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "bazaar.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                user_id INTEGER,
                username TEXT,
                product_id TEXT,
                product_name TEXT,
                amount INTEGER,
                status TEXT DEFAULT 'WAITING_PAYMENT',
                screenshot_file_id TEXT,
                utr_number TEXT,
                delivery_data TEXT,
                reject_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delivered_at TIMESTAMP
            )
        """)
        conn.commit()

def save_user(user_id: int, username: str, first_name: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name
        """, (user_id, username or "", first_name or ""))
        conn.commit()

def create_order(user_id: int, username: str, product_id: str, product_name: str, amount: int) -> str:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM orders")
        count = cursor.fetchone()[0] + 1001
        order_id = f"BB-{count}"
        cursor.execute("""
            INSERT INTO orders (order_id, user_id, username, product_id, product_name, amount, status)
            VALUES (?, ?, ?, ?, ?, ?, 'WAITING_PAYMENT')
        """, (order_id, user_id, username or "", product_id, product_name, amount))
        conn.commit()
        return order_id

def update_order_proof(order_id: str, file_id: str = None, utr: str = None):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE orders 
            SET status='PENDING_VERIFICATION',
                screenshot_file_id=COALESCE(?, screenshot_file_id),
                utr_number=COALESCE(?, utr_number)
            WHERE order_id=?
        """, (file_id, utr, order_id))
        conn.commit()

def mark_order_delivered(order_id: str, delivery_data: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE orders 
            SET status='DELIVERED',
                delivery_data=?,
                delivered_at=?
            WHERE order_id=?
        """, (delivery_data, now, order_id))
        conn.commit()

def mark_order_rejected(order_id: str, reason: str = "Payment verification failed"):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE orders 
            SET status='REJECTED',
                reject_reason=?
            WHERE order_id=?
        """, (reason, order_id))
        conn.commit()

def get_order(order_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE order_id=?", (order_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_orders(user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT 10", (user_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_stats():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM orders WHERE status='DELIVERED'")
        delivered_row = cursor.fetchone()
        delivered_count, total_revenue = delivered_row[0], delivered_row[1]
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status='PENDING_VERIFICATION'")
        pending_orders = cursor.fetchone()[0]
        return {
            "total_users": total_users,
            "total_orders": total_orders,
            "delivered_count": delivered_count,
            "total_revenue": total_revenue,
            "pending_orders": pending_orders
        }

def get_all_user_ids():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        return [row[0] for row in cursor.fetchall()]
