"""
Streak tracking and gamification functions.
"""
import aiosqlite
from datetime import date, timedelta
from config import DATABASE_PATH
import logging

logger = logging.getLogger(__name__)

async def update_streak(user_id: int):
    """
    Updates user's streak when they check weather.
    Returns: (current_streak, best_streak, is_new_record)
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Get current streak data
        async with db.execute(
            "SELECT current_streak, last_check_date, best_streak FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return (0, 0, False)
            
            current_streak = row['current_streak'] or 0
            last_check = row['last_check_date']
            best_streak = row['best_streak'] or 0
        
        today = date.today()
        
        # If never checked before
        if not last_check:
            new_streak = 1
            await db.execute(
                "UPDATE users SET current_streak = 1, last_check_date = ?, best_streak = 1 WHERE user_id = ?",
                (today.isoformat(), user_id)
            )
            await db.commit()
            return (1, 1, True)
        
        # Parse last check date
        last_date = date.fromisoformat(last_check)
        
        # Already checked today
        if last_date == today:
            return (current_streak, best_streak, False)
        
        # Checked yesterday - continue streak
        if last_date == today - timedelta(days=1):
            new_streak = current_streak + 1
        # Missed days - reset streak
        else:
            new_streak = 1
        
        # Update best streak if needed
        is_new_record = new_streak > best_streak
        new_best = max(new_streak, best_streak)
        
        await db.execute(
            "UPDATE users SET current_streak = ?, last_check_date = ?, best_streak = ? WHERE user_id = ?",
            (new_streak, today.isoformat(), new_best, user_id)
        )
        await db.commit()
        
        return (new_streak, new_best, is_new_record)

async def get_streak_info(user_id: int):
    """
    Returns user's streak information.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT current_streak, best_streak, last_check_date FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return {'current_streak': 0, 'best_streak': 0, 'last_check_date': None}
            
            return {
                'current_streak': row['current_streak'] or 0,
                'best_streak': row['best_streak'] or 0,
                'last_check_date': row['last_check_date']
            }

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
