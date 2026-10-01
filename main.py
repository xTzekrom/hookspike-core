from flask import Flask, render_template_string, request, session
from ai_engine import get_ai_response  # Humne pehli file ko yahan link kar diya!

app = Flask(__name__)
app.secret_key = 'hookspike_billionaire_modular_v2_secret'

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>HookSpike AI ⚡ - Ultra-Growth Creative Engine</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; padding: 20px; background-color: #030712; color: #f3f4f6; }
        .container { max-width: 500px; margin: 0 auto; background: #0b0f19; padding: 30px; border-radius: 24px; box-shadow: 0 0 40px rgba(102, 252, 241, 0.2); border: 1px solid #1f2937; backdrop-filter: blur(10px); }
        .logo { font-size: 36px; font-weight: 900; color: #66fcf1; letter-spacing: -0.5px; text-shadow: 0 0 25px rgba(102, 252, 241, 0.5); }
        .logo span { color: #f59e0b; text-shadow: 0 0 25px rgba(245, 158, 11, 0.5); }
        p.tagline { color: #9ca3af; font-size: 13px; margin-top: 5px; margin-bottom: 25px; font-weight: 600; text-transform: uppercase; letter-spacing: 2px; }
        .counter-badge { display: inline-block; padding: 8px 16px; background: #111827; border-radius: 20px; font-size: 13px; color: #66fcf1; border: 1px solid #00ffcc; margin-bottom: 20px; box-shadow: inset 0 0 10px rgba(0, 255, 204, 0.2); font-weight: bold; }
        select, input[type="text"] { width: 100%; padding: 16px; border: 2px solid #1f2937; border-radius: 14px; background-color: #111827; color: white; font-size: 16px; margin-bottom: 20px; outline: none; box-sizing: border-box; transition: 0.3s; }
        input[type="text"]:focus, select:focus { border-color: #66fcf1; box-shadow: 0 0 20px rgba(102, 252, 241, 0.3); }
        button { width: 100%; padding: 16px; color: #030712; background-color: #66fcf1; border: none; border-radius: 14px; font-weight: bold; font-size: 18px; cursor: pointer; transition: 0.3s; box-shadow: 0 4px 20px rgba(102, 252, 241, 0.4); text-transform: uppercase; letter-spacing: 0.5px; }
        button:hover { background-color: #45a29e; transform: translateY(-2px); box-shadow: 0 6px 25px rgba(102, 252, 241, 0.6); }
        .copy-btn { width: auto; display: inline-block; margin-top: 15px; padding: 10px 20px; background-color: #f59e0b; color: #030712; border-radius: 10px; font-size: 14px; cursor: pointer; font-weight: bold; border: none; }
        .loader { display: none; margin: 25px auto; border: 4px solid #1f2937; border-radius: 50%; border-top: 4px solid #66fcf1; width: 45px; height: 45px; animation: spin 0.8s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .loading-text { display: none; color: #66fcf1; font-size: 14px; font-style: italic; font-weight: 500; }
        .result-box { text-align: left; margin-top: 35px; padding: 25px; background-color: #111827; border-radius: 18px; border-top: 4px solid #f59e0b; white-space: pre-wrap; font-size: 15px; line-height: 1.8; color: #e5e7eb; border-left: 1px solid #1f2937; }
        .result-box h3 { margin-top: 0; color: #f59e0b; font-size: 20px; font-weight: 800; border-bottom: 1px solid #1f2937; padding-bottom: 10px; }
        .paywall-box { margin-top: 20px; padding: 30px; background: #1a0b0e; border: 2px dashed #f43f5e; border-radius: 20px; text-align: center; box-shadow: 0 0 30px rgba(244, 63, 94, 0.25); }
        .paywall-box h2 { color: #f43f5e; margin-top: 0; font-size: 24px; font-weight: 900; text-transform: uppercase; }
        .paywall-box p { color: #e5e7eb; font-size: 15px; margin-bottom: 25px; }
        .pricing-plan { display: flex; justify-content: space-around; margin-bottom: 25px; gap: 15px; }
        .plan-card { background: #111827; padding: 15px; border-radius: 12px; border: 1px solid #374151; width: 48%; }
        .plan-card h4 { margin: 0; color: #66fcf1; font-size: 15px; text-transform: uppercase; }
        .plan-card p { margin: 8px 0 0 0; font-size: 22px; font-weight: bold; color: white; }
        .upi-details { font-size: 18px; font-weight: bold; color: #66fcf1; background: #030712; padding: 14px; border-radius: 10px; border: 1px solid #1f2937; margin-bottom: 15px; }
    </style>
    <script>
        function showLoading() {
            var btn = document.getElementById("submitBtn");
            if(btn) {
                btn.style.display = "none";
                document.getElementById("loaderIcon").style.display = "block";
                document.getElementById("loaderText").style.display = "block";
            }
        }
        function copyText() {
            var textToCopy = document.getElementById("rawText").innerText;
            navigator.clipboard.writeText(textToCopy);
            var copyBtn = document.getElementById("copyBtnText");
            copyBtn.innerText = "📋 Strategy Copied!";
            setTimeout(function(){ copyBtn.innerText = "📋 Copy Strategy Data"; }, 2000);
        }
    </script>
</head>
<body>
    <div class="container">
        <div class="logo">Hook<span>Spike</span> AI ⚡</div>
        <p class="tagline">Ultra-Growth Creative Engine</p>
        
        <div class="counter-badge">⚡ Neural Tokens: {{ 9 - count }} / 9 Free Generations Left</div>

        {% if show_paywall %}
        <div class="paywall-box">
            <h2>🔒 Commercial License Locked</h2>
            <p>You have successfully utilized your 9 free creator tokens. Upgrade to keep deployment nodes active:</p>
            <div class="pricing-plan">
                <div class="plan-card"><h4>Weekly Pack</h4><p>₹23</p></div>
                <div class="plan-card"><h4>Monthly Pro</h4><p>₹49</p></div>
            </div>
            <div class="upi-details">Transfer Plan Amount to: hookspike@upi</div>
            <p style="font-size: 12px; color: #9ca3af;">Ping payment receipt to billing@hookspike.ai for instant activation.</p>
            <a href="/" style="color: #66fcf1; text-decoration: none; font-size: 13px; font-weight: bold;">🔄 Reset Demo Engine Tokens</a>
        </div>
        {% else %}
        <form method="POST" onsubmit="showLoading()">
            <select name="platform_type">
                <option value="youtube" {% if platform_type == 'youtube' %}selected{% endif %}>🎥 YouTube Engine (Hooks & Thumbnails)</option>
                <option value="instagram" {% if platform_type == 'instagram' %}selected{% endif %}>📱 Instagram Reels Engine (Viral Scripts & Hooks)</option>
                <option value="global_ai" {% if platform_type == 'global_ai' %}selected{% endif %}>🌐 HookSpike Core AI Search (Global Intelligence)</option>
            </select>
            <input type="text" name="topic" placeholder="Enter topic, script concept, or global query..." value="{{ topic }}" required><br>
            <button type="submit" id="submitBtn">Launch AI Strategy Engine 🚀</button>
        </form>
        {% endif %}

        <div id="loaderIcon" class="loader"></div>
        <div id="loaderText" class="loading-text">⚡ HookSpike Intelligence Core Mining Data...</div>

        {% if result and not show_paywall %}
        <div class="result-box">
            <h3>📊 Engine Output Matrix Unlocked:</h3>
            <div id="rawText">{{ result }}</div>
            <button id="copyBtnText" class="copy-btn" onclick="copyText()">📋 Copy Strategy Data</button>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if 'search_count' not in session:
        session['search_count'] = 0
        
    result = None
    topic = ""
    platform_type = "youtube"
    show_paywall = False

    if request.method == "GET" and session['search_count'] >= 9:
        session['search_count'] = 0 

    if request.method == "POST":
        session['search_count'] += 1
        platform_type = request.form.get("platform_type")
        topic = request.form.get("topic")
        
        if session['search_count'] > 9:
            show_paywall = True
        else:
            # Humne dusri file ke dimaag ko call kiya aur result nikal liya!
            result = get_ai_response(platform_type, topic)
            
    return render_template_string(HTML_TEMPLATE, result=result, topic=topic, platform_type=platform_type, count=min(session['search_count'], 9), show_paywall=show_paywall)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
