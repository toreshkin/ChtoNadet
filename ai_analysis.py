"""
AI-powered clothing analysis using Google Gemini Vision
"""
import google.generativeai as genai
import json
import logging
from typing import Dict, Optional
from io import BytesIO

logger = logging.getLogger(__name__)

# Initialize Gemini
def init_gemini(api_key: str):
    if not api_key:
        logger.warning("Gemini API Key missing. AI features disabled.")
        return
    genai.configure(api_key=api_key)
    
    # Log available models
    try:
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods:
                logger.info(f"Available Gemini model: {model.name}")
    except Exception as e:
        logger.error(f"Could not list models: {e}")

async def analyze_clothing_photo(photo_bytes: bytes) -> Dict:
    """
    Analyze clothing photo using Gemini Vision with automatic model fallback
    """
    import PIL.Image
    
    # Prepare image
    try:
        image = PIL.Image.open(BytesIO(photo_bytes))
    except Exception as e:
        return {'success': False, 'error': f"Image load error: {e}"}

    # Prompt
    prompt = """
    Проанализируй эту одежду и опиши:
    1. Тип одежды (футболка, куртка, свитер, джинсы и т.д.)
    2. Материал (если виден: хлопок, шерсть, синтетика, джинса)
    3. Степень теплоты: легкая/средняя/теплая/очень теплая
    4. Подходящий температурный диапазон в °C (например: от 15 до 25)
    5. Стиль: casual/formal/sport
    
    Ответь ТОЛЬКО в формате JSON без дополнительного текста:
    {
      "clothing_type": "тип одежды",
      "material": "материал или неизвестно",
      "warmth_level": "легкая|средняя|теплая|очень теплая",
      "suitable_temp_min": число,
      "suitable_temp_max": число,
      "style": "casual|formal|sport",
      "description": "краткое описание на русском"
    }
    """

    # List of models to try in order
    # Using 'latest' aliases where appropriate or strictly known working models
    candidates = [
        'gemini-1.5-flash',
        'gemini-1.5-flash-latest',
        'gemini-1.5-pro',
        'gemini-1.5-pro-latest',
    ]

    last_error = None
    
    for model_name in candidates:
        try:
            logger.info(f"Attempting analysis with model: {model_name}")
            model = genai.GenerativeModel(model_name)
            
            # This is the actual network call that might fail
            response = model.generate_content([prompt, image])
            
            # Parse JSON
            response_text = response.text.strip()
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
            
            data = json.loads(response_text)
            data['success'] = True
            logger.info(f"Success with model: {model_name}")
            return data
            
        except Exception as e:
            logger.warning(f"Model {model_name} failed: {e}")
            last_error = e
            continue
    
    logger.error("All Gemini models failed")
    return {
        'success': False,
        'error': f"AI Analysis failed. Last error: {str(last_error)}"
    }

async def analyze_clothing_text(text_description: str) -> Dict:
    """
    Analyze clothing based on text description using Gemini
    """
    prompt = f"""
    Проанализируй это описание одежды: "{text_description}"
    
    Опиши:
    1. Тип одежды (футболка, куртка, свитер, джинсы и т.д.)
    2. Материал (предположи по типу, если не указан)
    3. Степень теплоты: легкая/средняя/теплая/очень теплая
    4. Подходящий температурный диапазон в °C (например: от 15 до 25)
    5. Стиль: casual/formal/sport
    
    Ответь ТОЛЬКО в формате JSON без дополнительного текста:
    {{
      "clothing_type": "тип одежды",
      "material": "материал",
      "warmth_level": "легкая|средняя|теплая|очень теплая",
      "suitable_temp_min": число,
      "suitable_temp_max": число,
      "style": "casual|formal|sport",
      "description": "краткое описание на русском"
    }}
    """

    # Updated model list with latest aliases
    candidates = [
        'gemini-1.5-flash',
        'gemini-1.5-flash-latest',
        'gemini-1.5-pro',
        'gemini-1.5-pro-latest',
    ]
    last_error = None
    
    for model_name in candidates:
        try:
            logger.info(f"Attempting text analysis with model: {model_name}")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            response_text = response.text.strip()
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
            
            data = json.loads(response_text)
            data['success'] = True
            logger.info(f"Success with model: {model_name}")
            return data
            
        except Exception as e:
            logger.warning(f"Model {model_name} failed: {e}")
            last_error = e
            continue
            
    return {'success': False, 'error': f"Analysis failed: {str(last_error)}"}

def generate_clothing_recommendation(clothing_data: Dict, weather_data: Dict, user_name: str) -> str:
    """
    Generate recommendation message comparing clothing with weather
    """
    current_temp = weather_data['main']['temp']
    suitable_min = clothing_data.get('suitable_temp_min', -50)
    suitable_max = clothing_data.get('suitable_temp_max', 50)
    
    verdict = ""
    emoji = ""
    advice = ""

    if suitable_min <= current_temp <= suitable_max:
        verdict = '✅ Отлично подходит!'
        emoji = '👍'
        advice = f'Эта {clothing_data.get("clothing_type", "одежда")} идеальна для сегодняшней погоды ({current_temp:+.0f}°C)!'
    
    elif current_temp < suitable_min:
        diff = suitable_min - current_temp
        verdict = '❄️ Будет холодно'
        emoji = '🥶'
        advice = f'Для {current_temp:+.0f}°C это слишком легко. Вам может быть холодно (на {diff:.0f}°C холоднее комфортного диапазона).'
        
    elif current_temp > suitable_max:
        diff = current_temp - suitable_max
        verdict = '🔥 Будет жарко'
        emoji = '🥵'
        advice = f'При {current_temp:+.0f}°C в этом будет жарко (на {diff:.0f}°C теплее комфортного диапазона).'

    return f"""
<b>📸 Анализ одежды</b>
🧥 <b>Тип:</b> {clothing_data.get('clothing_type')}
🧵 <b>Материал:</b> {clothing_data.get('material')}
🌡️ <b>Теплота:</b> {clothing_data.get('warmth_level')}
📊 <b>Подходит для:</b> {suitable_min}°C ... {suitable_max}°C
👔 <b>Стиль:</b> {clothing_data.get('style')}

━━━━━━━━━━━━━━━
<b>{emoji} Погода сегодня:</b> {current_temp:+.0f}°C
<b>{verdict}</b>
{advice}

━━━━━━━━━━━━━━━
💡 <i>{clothing_data.get('description', '')}</i>
"""
