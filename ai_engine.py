import os
from google import genai
from google.genai import types

# रेंडर के Environment Variables से सीधे चाबियों को उठाना 🚀
PRIMARY_KEY = os.environ.get('PRIMARY_KEY', 'YOUR_NEW_KEY_1')
BACKUP_KEY = os.environ.get('BACKUP_KEY', 'YOUR_NEW_KEY_2')

def get_ai_response(platform_type, topic):
    # यह तय करता है कि कौन सी चाबी चालू है
    api_key = PRIMARY_KEY if PRIMARY_KEY != 'YOUR_NEW_KEY_1' else None
    
    if not api_key:
        return "❌ Error: Render Dashboard में आपकी API Key लोड नहीं हो पाई है। कृपया Environment Variables चेक करें।"

    try:
        # असली एआई क्लाइंट को चालू करना
        client = genai.Client(api_key=api_key)
        
        # प्रॉम्प्ट सेटिंग्स
        if platform_type == "youtube":
            prompt = (
                f"You are a master YouTube viral marketing specialist. For the video concept '{topic}', "
                f"generate 3 highly compelling hooks with maximum audience retention and "
                f"3 descriptive high-CTR visual prompts for thumbnails. Output everything strictly in English. "
                f"Do not mention any AI engine brand names. Format beautifully with engaging emojis."
            )
        elif platform_type == "instagram":
            prompt = (
                f"You are an elite Instagram Reels growth expert. For the reel concept '{topic}', "
                f"provide 3 hyper-engaging 3-second opening visual/text hooks to stop users from scrolling. "
                f"Also, write a high-retention 15-second viral video script structure along with trending caption ideas and 5 high-reach hashtags. "
                f"Output everything strictly in English with engaging emojis."
            )
        else:
            prompt = (
                f"You are an ultra-advanced AI search engine like Google and ChatGPT combined. Answer the following user query: '{topic}'. "
                f"Provide an extremely smart, accurate, deep-dive analytical response. "
                f"Break down complex ideas into crisp professional points. Output everything strictly in English with proper headings and emojis."
            )

        # लाइव एआई कंटेंट जनरेशन
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.7)
        )
        return response.text

    except Exception as e:
        # अगर कोई गड़बड़ होगी तो यह असली समस्या स्क्रीन पर दिखाएगा
        return f"❌ AI Engine Error: {str(e)}. कृपया अपनी API Key की वैधता जांचें।"
