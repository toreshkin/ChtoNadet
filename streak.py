"""
Streak tracking using SQLAlchemy (PostgreSQL/SQLite compatible)
"""
from database import get_session
from sqlalchemy import text
from datetime import date, datetime, timedelta
import logging

logger = logging.getLogger(__name__)

async def update_streak(user_id: int):
    """
    Update and return user's weather check streak.
    Returns: (current_streak, best_streak, is_new_record)
    """
    try:
        async with get_session() as session:
            # Get user's current streak data
            result = await session.execute(
                text("SELECT last_check_date, current_streak, best_streak FROM users WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            row = result.fetchone()
            
            if not row:
                return 0, 0, False
            
            last_check_raw, current_streak, best_streak = row
            current_streak = current_streak or 0
            best_streak = best_streak or 0
            today = date.today()
            
            # Handle date parsing from string or date object (SQLAlchemy/DB behavior varies)
            last_check = None
            if last_check_raw:
                if isinstance(last_check_raw, str):
                    last_check = date.fromisoformat(last_check_raw)
                elif isinstance(last_check_raw, datetime):
                    last_check = last_check_raw.date()
                else:
                    last_check = last_check_raw

            # Calculate new streak
            if not last_check:
                current_streak = 1
            else:
                days_diff = (today - last_check).days
                
                if days_diff == 1:
                    # Consecutive day
                    current_streak += 1
                elif days_diff == 0:
                    # Already checked today
                    return current_streak, best_streak, False
                else:
                    # Streak broken
                    current_streak = 1
            
            # Check for new record
            is_new_record = current_streak > best_streak
            if is_new_record:
                best_streak = current_streak
            
            # Update database
            await session.execute(
                text("""
                    UPDATE users 
                    SET last_check_date = :today, 
                        current_streak = :current_streak,
                        best_streak = :best_streak
                    WHERE user_id = :user_id
                """),
                {
                    "today": today.isoformat(),
                    "current_streak": current_streak,
                    "best_streak": best_streak,
                    "user_id": user_id
                }
            )
            
            return current_streak, best_streak, is_new_record
            
    except Exception as e:
        logger.error(f"Error updating streak for user {user_id}: {e}")
        return 0, 0, False

async def get_streak_info(user_id: int):
    """
    Returns user's streak information.
    """
    try:
        async with get_session() as session:
            result = await session.execute(
                text("SELECT current_streak, best_streak, last_check_date FROM users WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            row = result.fetchone()
            
            if not row:
                return {'current_streak': 0, 'best_streak': 0, 'last_check_date': None}
            
            return {
                'current_streak': row[0] or 0,
                'best_streak': row[1] or 0,
                'last_check_date': row[2]
            }
    except Exception as e:
        logger.error(f"Error getting streak info for user {user_id}: {e}")
        return {'current_streak': 0, 'best_streak': 0, 'last_check_date': None}

def get_streak_message(streak: int, is_new_record: bool = False) -> str:
    """
    Generates motivational message based on streak.
    """
    if is_new_record and streak > 1:
        return f"🎉 <b>НОВЫЙ РЕКОРД!</b> Серия: {streak} дней подряд! 🏆"
    
    if streak == 1:
        return "🔥 Начало серии! Проверяйте погоду каждый день, чтобы увеличить счётчик."
    elif streak < 7:
        return f"🔥 Серия: {streak} дней! Продолжайте в том же духе! 💪"
    elif streak < 30:
        return f"🔥🔥 Отличная серия: {streak} дней! Вы молодец! 🌟"
    else:
        return f"🔥🔥🔥 НЕВЕРОЯТНО! Серия: {streak} дней! Вы легенда! 👑"
