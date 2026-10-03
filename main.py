import os
import sys
import time

from flask import (
    Flask,
    render_template_string,
    request,
    session,
    redirect,
    url_for,
    send_file,
    jsonify,
)

from supabase import create_client, Client
from supabase.client import ClientOptions
from supabase_auth import SyncSupportedStorage


# ============================================================
# AI ENGINE
# ============================================================

try:
    from ai_engine import (
        get_ai_response,
        generate_thumbnail_image,
        generate_creator_pack,
        refine_creator_content,
        analyze_hook,
        discover_topics,
    )
except ImportError:
    print("CRITICAL ERROR: 'ai_engine.py' file not found!")
    sys.exit(1)


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)

# IMPORTANT:
# Render Dashboard -> Environment Variables me
# FLASK_SECRET_KEY set karna recommended hai.
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "CHANGE_THIS_SECRET_IN_RENDER"
)

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30,
)


# ============================================================
# FLASK SESSION STORAGE FOR SUPABASE PKCE
# ============================================================

class FlaskSessionStorage(SyncSupportedStorage):

    def __init__(self):
        self.storage = session

    def get_item(self, key: str):
        return self.storage.get(key)

    def set_item(self, key: str, value: str):
        self.storage[key] = value

    def remove_item(self, key: str):
        self.storage.pop(key, None)


# ============================================================
# SUPABASE
# ============================================================

SUPABASE_URL = os.environ.get("VITE_SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("VITE_SUPABASE_ANON_KEY")

supabase = None

if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(
                storage=FlaskSessionStorage(),
                flow_type="pkce",
            ),
        )

        print("Supabase client initialized successfully.")

    except Exception as e:
        print(f"CRITICAL: Supabase initialization failed: {e}")
        supabase = None

else:
    print(
        "WARNING: VITE_SUPABASE_URL or "
        "VITE_SUPABASE_ANON_KEY is missing."
    )


# ============================================================
# HTML
# ============================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>

<head>

    <meta
        name="google-site-verification"
        content="EOl-njARKhvmSLTzhuBy-3xJ8kchPVDb38nV-KzuLfk"
    />

    <title>HookSpike AI ⚡ - Ultra-Growth Creative Engine</title>

    <link rel="icon" type="image/png" href="/favicon.png?v=2">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <style>

        body {
            font-family: 'Segoe UI', sans-serif;
            text-align: center;
            padding: 20px;
            background:
                radial-gradient(
                    circle at center,
                    #0d1527 0%,
                    #030712 100%
                );
            color: #f3f4f6;
            margin: 0;
        }
        /* --- Naya Creative Feature CSS --- */
        .hook-card {
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 16px;
            padding: 20px;
            margin-top: 15px;
            border-left: 4px solid #f59e0b;
            transition: all 0.3s ease;
        }
        .hook-card:hover {
            border-color: #66fcf1;
            box-shadow: 0 0 15px rgba(102, 252, 241, 0.2);
        }
        .cue-box {
            background: rgba(245, 158, 11, 0.05);
            border: 1px dashed rgba(245, 158, 11, 0.3);
            border-radius: 10px;
            padding: 12px;
            margin-top: 15px;
            font-size: 13px;
            color: #9ca3af;
            text-align: left;
        }
        .cue-box strong {
            color: #f59e0b;
        }
        .copy-btn.copied {
            background: linear-gradient(90deg, #10b981, #059669) !important;
            color: white !important;
            box-shadow: 0 0 15px rgba(16, 185, 129, 0.4);
        }
        

        .container {
            max-width: 500px;
            margin: 40px auto;
            background: rgba(11, 15, 25, 0.85);
            padding: 35px;
            border-radius: 24px;
            box-shadow:
                0 0 50px rgba(102, 252, 241, 0.15);
            border: 2px solid #1f2937;
            backdrop-filter: blur(15px);
        }

        .logo {
            font-size: 40px;
            font-weight: 900;
            color: #66fcf1;
            text-shadow:
                0 0 30px rgba(102, 252, 241, 0.6);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .logo span {
            color: #f59e0b;
        }

        p.tagline {
            color: #9ca3af;
            font-size: 12px;
            margin-top: 5px;
            margin-bottom: 30px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 3px;
        }

        .counter-badge {
            display: inline-block;
            padding: 8px 18px;
            background: rgba(17, 24, 39, 0.9);
            border-radius: 30px;
            font-size: 13px;
            color: #66fcf1;
            border: 1px solid #00ffcc;
            margin-bottom: 25px;
            font-weight: bold;
        }

        .login-box {
            padding: 20px;
            text-align: center;
        }

        .google-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            width: 100%;
            padding: 16px;
            background: white;
            color: #1f2937;
            border-radius: 14px;
            font-weight: 700;
            font-size: 16px;
            text-decoration: none;
            border: 1px solid #e5e7eb;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            box-sizing: border-box;
            transition:
                transform 0.2s,
                box-shadow 0.2s;
        }

        .google-btn:hover {
            box-shadow: 0 6px 18px rgba(0,0,0,0.2);
        }

        .google-btn:active {
            transform: scale(0.98);
        }

        .google-icon {
            font-size: 22px;
            font-weight: 900;
        }

        .user-profile {
            font-size: 12px;
            color: #9ca3af;
            margin-bottom: 15px;
            text-align: right;
        }

        .logout-link {
            color: #f43f5e;
            text-decoration: none;
            margin-left: 8px;
            font-weight: bold;
        }

        label {
            display: block;
            text-align: left;
            font-size: 11px;
            color: #66fcf1;
            text-transform: uppercase;
            margin-bottom: 8px;
            font-weight: 700;
        }

        select,
        input[type="text"] {
            width: 100%;
            padding: 18px;
            border: 2px solid #1f2937;
            border-radius: 14px;
            background-color: #0d111a;
            color: white;
            font-size: 16px;
            margin-bottom: 25px;
            outline: none;
            box-sizing: border-box;
        }

        button {
            width: 100%;
            padding: 18px;
            color: #030712;
            background:
                linear-gradient(
                    90deg,
                    #66fcf1,
                    #45a29e
                );
            border: none;
            border-radius: 16px;
            font-weight: 800;
            font-size: 18px;
            cursor: pointer;
            text-transform: uppercase;
        }

        .copy-btn {
            width: auto;
            display: inline-block;
            margin-top: 15px;
            padding: 10px 22px;
            background:
                linear-gradient(
                    90deg,
                    #f59e0b,
                    #d97706
                );
            color: #030712;
            border-radius: 10px;
            font-weight: bold;
            border: none;
            cursor: pointer;
        }

        .loader {
            display: none;
            margin: 25px auto;
            border: 4px solid #1f2937;
            border-radius: 50%;
            border-top: 4px solid #66fcf1;
            width: 45px;
            height: 45px;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            0% {
                transform: rotate(0deg);
            }

            100% {
                transform: rotate(360deg);
            }
        }

        .loading-text {
            display: none;
            color: #66fcf1;
            font-size: 14px;
            font-style: italic;
        }

        .result-box {
            text-align: left;
            margin-top: 35px;
            padding: 25px;
            background-color: #0d111a;
            border-radius: 20px;
            border-top: 4px solid #f59e0b;
            white-space: pre-wrap;
            font-size: 15px;
            line-height: 1.8;
            color: #e5e7eb;
            border-left: 1px solid #1f2833;
        }

        .result-box h3 {
            margin-top: 0;
            color: #f59e0b;
            font-size: 20px;
            font-weight: 800;
        }
        .content-selector { display: grid; gap: 12px; margin-bottom: 24px; }
        .content-option { position: relative; }
        .content-option input { position: absolute; opacity: 0; pointer-events: none; }
        .content-option label {
            display:flex; align-items:center; gap:14px; width:100%; box-sizing:border-box;
            padding:16px 18px; margin:0; border:1px solid #263244; border-radius:16px;
            background:linear-gradient(135deg,#0d111a,#111827); color:#e5e7eb;
            text-transform:none; font-size:15px; letter-spacing:0; cursor:pointer; transition:.2s;
        }
        .content-option label:hover { border-color:#66fcf1; transform:translateY(-1px); }
        .content-option input:checked + label {
            border-color:#66fcf1; box-shadow:0 0 22px rgba(102,252,241,.14);
            background:linear-gradient(135deg,#10202a,#111827);
        }
        .option-icon { font-size:26px; min-width:32px; }
        .option-copy { text-align:left; }
        .option-title { display:block; color:#fff; font-weight:900; font-size:16px; }
        .option-sub { display:block; color:#8b96a8; font-size:12px; margin-top:3px; }
        .result-header { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:15px; }
        .result-type {
            display:inline-flex; padding:7px 11px; border-radius:999px;
            background:rgba(102,252,241,.08); border:1px solid rgba(102,252,241,.25);
            color:#66fcf1; font-size:11px; font-weight:900; text-transform:uppercase; letter-spacing:1px;
        }
        .thumbnail-preview { width:100%; display:block; margin-top:18px; border-radius:16px; border:1px solid #263244; box-shadow:0 12px 35px rgba(0,0,0,.35); }
        .idea-note,.research-note { margin-top:12px; padding:12px 14px; border-radius:12px; font-size:12px; line-height:1.55; }
        .generate-image-btn {
            width: 100%;
            margin-top: 12px;
            padding: 13px 18px;
            border-radius: 12px;
            border: 1px solid #374151;
            background: linear-gradient(90deg, #7c3aed, #4f46e5);
            color: white;
            font-weight: 800;
            font-size: 14px;
            cursor: pointer;
            text-transform: none;
        }
        .generate-image-btn:disabled {
            opacity: 0.65;
            cursor: wait;
        }
        .image-status {
            margin-top: 12px;
            padding: 12px 14px;
            border-radius: 12px;
            background: rgba(31, 41, 55, 0.65);
            border: 1px dashed #374151;
            color: #9ca3af;
            font-size: 13px;
            line-height: 1.5;
            text-align: center;
        }
        .image-status.error {
            color: #fca5a5;
            border-color: rgba(239, 68, 68, 0.35);
            background: rgba(127, 29, 29, 0.12);
        }

        .idea-note { background:rgba(245,158,11,.07); border:1px dashed rgba(245,158,11,.35); color:#cbd5e1; }
        .research-note { background:rgba(102,252,241,.045); border:1px solid rgba(102,252,241,.12); color:#94a3b8; }


        /* --- CREATOR STUDIO UI --- */
        .studio-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; margin:24px 0; }
        .studio-card { text-align:left; padding:17px; border:1px solid #263244; border-radius:18px; background:linear-gradient(145deg,#0d111a,#111827); cursor:pointer; transition:.2s; }
        .studio-card:hover { transform:translateY(-2px); border-color:#66fcf1; box-shadow:0 10px 30px rgba(0,0,0,.25); }
        .studio-card .icon { font-size:25px; }
        .studio-card strong { display:block; color:#fff; margin-top:7px; font-size:14px; }
        .studio-card span { display:block; color:#8b96a8; font-size:11px; line-height:1.45; margin-top:4px; }
        .tool-panel { display:none; margin-top:18px; padding:18px; border:1px solid #263244; border-radius:18px; background:rgba(13,17,26,.75); text-align:left; }
        .tool-panel.show { display:block; animation:fadeIn .25s ease; }
        @keyframes fadeIn { from {opacity:0; transform:translateY(5px)} to {opacity:1; transform:translateY(0)} }
        .tool-title { color:#66fcf1; font-weight:900; margin-bottom:10px; }
        .tool-input { width:100%; min-height:100px; resize:vertical; padding:13px; box-sizing:border-box; border:1px solid #263244; border-radius:12px; background:#080c14; color:#fff; outline:none; }
        .tool-select { width:100%; padding:13px; border:1px solid #263244; border-radius:12px; background:#080c14; color:#fff; margin:8px 0 12px; }
        .tool-action { width:100%; padding:12px; border-radius:12px; border:1px solid #374151; background:linear-gradient(90deg,#66fcf1,#45a29e); color:#030712; font-weight:900; cursor:pointer; text-transform:none; font-size:14px; }
        .tool-output { margin-top:14px; padding:14px; border-radius:14px; background:#080c14; border:1px solid #1f2937; white-space:pre-wrap; line-height:1.65; font-size:13px; color:#dbe4ee; }
        .quick-actions { display:flex; flex-wrap:wrap; gap:8px; margin-top:15px; }
        .quick-btn { width:auto; padding:9px 12px; border-radius:999px; border:1px solid #334155; background:#111827; color:#dbe4ee; font-size:12px; cursor:pointer; text-transform:none; }
        .quick-btn:hover { border-color:#66fcf1; color:#66fcf1; }
        .pack-banner { margin-top:18px; padding:16px; border-radius:18px; background:linear-gradient(135deg,rgba(102,252,241,.08),rgba(124,58,237,.10)); border:1px solid rgba(102,252,241,.18); text-align:left; }
        .pack-banner strong { color:#fff; }
        .pack-banner span { display:block; color:#94a3b8; font-size:12px; line-height:1.5; margin-top:5px; }
        .history-list { max-height:220px; overflow:auto; margin-top:10px; }
        .history-item { padding:10px; border-bottom:1px solid #1f2937; cursor:pointer; color:#cbd5e1; font-size:12px; }
        .history-item:hover { color:#66fcf1; }
        @media(max-width:560px){ .studio-grid{grid-template-columns:1fr;} }

        /* --- PREMIUM COMMERCIAL PAYWALL SUITE --- */
        .paywall-box {
            margin-top: 30px;
            padding: 40px 25px;
            background: linear-gradient(135deg, #0b1528 0%, #030712 100%);
            border: 2px solid #ef4444;
            border-radius: 28px;
            box-shadow: 0 0 35px rgba(239, 68, 68, 0.15);
            position: relative;
            overflow: hidden;
        }
        .paywall-box::before {
            content: '';
            position: absolute;
            top: 0; left: 0; width: 100%; height: 4px;
            background: linear-gradient(90deg, #ef4444, #f59e0b);
        }
        .paywall-box h2 {
            color: #ef4444;
            font-size: 24px;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        .paywall-box p.pay-desc {
            color: #9ca3af;
            font-size: 14px;
            line-height: 1.6;
            margin-bottom: 30px;
        }
        .pricing-plan {
            display: flex;
            flex-direction: column;
            gap: 20px;
            margin-bottom: 35px;
        }
        .plan-card {
            background: #0d111a;
            padding: 22px;
            border-radius: 18px;
            border: 1px solid #1f2937;
            text-align: left;
            position: relative;
            transition: all 0.3s ease;
            box-sizing: border-box;
            width: 100% !important;
        }
        .plan-card:hover {
            border-color: #66fcf1;
            box-shadow: 0 0 20px rgba(102, 252, 241, 0.1);
        }
        .plan-card.popular {
            border: 2px solid #f59e0b;
        }
        .plan-badge {
            position: absolute;
            top: -12px; right: 15px;
            background: #f59e0b;
            color: #030712;
            font-size: 10px;
            font-weight: 900;
            padding: 4px 10px;
            border-radius: 20px;
            text-transform: uppercase;
        }
        .plan-card h4 {
            margin: 0;
            color: #66fcf1;
            font-size: 16px;
            font-weight: 800;
        }
        .plan-card p.plan-sub {
            margin: 4px 0 12px 0;
            color: #6b7280;
            font-size: 12px;
        }
        .plan-price-row {
            display: flex;
            align-items: baseline;
            gap: 6px;
        }
        .plan-card p.price {
            margin: 0;
            font-size: 32px;
            font-weight: 900;
            color: #ffffff;
        }
        .plan-card span.duration {
            color: #9ca3af;
            font-size: 14px;
        }
        .upi-details {
            font-size: 15px;
            font-weight: 700;
            color: #66fcf1;
            background: rgba(17, 24, 39, 0.8);
            padding: 16px;
            border-radius: 14px;
            border: 1px solid #1f2937;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .pay-btn {
            display: block;
            width: 100%;
            padding: 18px;
            background: linear-gradient(90deg, #66fcf1, #45a29e);
            color: #030712;
            text-decoration: none;
            border-radius: 16px;
            font-weight: 800;
            font-size: 16px;
            text-transform: uppercase;
            box-shadow: 0 4px 20px rgba(102, 252, 241, 0.2);
            box-sizing: border-box;
            transition: all 0.2s ease;
        }
        .pay-btn:hover {
            box-shadow: 0 6px 25px rgba(102, 252, 241, 0.3);
            transform: translateY(-2px);
        }


    </style>

    <script>

        function showLoading() {

            var submitBtn =
                document.getElementById("submitBtn");

            var loader =
                document.getElementById("loaderIcon");

            var loaderText =
                document.getElementById("loaderText");

            if (submitBtn) {
                submitBtn.style.display = "none";
            }

            if (loader) {
                loader.style.display = "block";
            }

            if (loaderText) {
                loaderText.style.display = "block";
            }
        }


        async function generateThumbnailImage() {
            const btn = document.getElementById("generateImageBtn");
            const status = document.getElementById("imageStatus");
            const imageBox = document.getElementById("generatedImageBox");
            const topicInput = document.querySelector('input[name="topic"]');
            const rawText = document.getElementById("rawText");

            if (!btn || !status || !imageBox || !topicInput || !rawText) return;

            btn.disabled = true;
            btn.innerText = "⏳ Generating thumbnail idea...";
            status.className = "image-status";
            status.innerText = "✨ Creating your visual idea...";
            imageBox.innerHTML = "";

            try {
                const response = await fetch("/generate-thumbnail", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        topic: topicInput.value,
                        thumbnail_text: rawText.innerText || rawText.textContent || ""
                    })
                });

                const data = await response.json();

                if (data.ok && data.image) {
                    const img = document.createElement("img");
                    img.className = "thumbnail-preview";
                    img.src = data.image;
                    img.alt = "AI-generated thumbnail idea";
                    imageBox.appendChild(img);

                    status.className = "image-status";
                    status.innerHTML = "💡 <strong>It’s an idea for your thumbnail.</strong> Use it as inspiration for your final design.";
                    btn.innerText = "🖼️ Generate Again";
                } else {
                    status.className = "image-status error";
                    status.innerText = data.error || "⚠️ Image server is busy — thumbnail image can't be generated right now.";
                    btn.innerText = "🖼️ Try Generate Image Again";
                }
            } catch (error) {
                console.error(error);
                status.className = "image-status error";
                status.innerText = "⚠️ Image server is busy — thumbnail image can't be generated right now.";
                btn.innerText = "🖼️ Try Generate Image Again";
            } finally {
                btn.disabled = false;
            }
        }

         function copyText() {
            var element = document.getElementById("rawText");
            if (!element) return;

            var text = element.innerText || element.textContent;

            // --- AI Text Enhancer Engine (Auto Formatting & Emojis) ---
            let formattedText = text;
            const boostWords = {
                "problem": "⚠️ MASSIVE PROBLEM",
                "delay": "🚨 UNANNOUNCED DELAY",
                "secret": "🤫 SECRET DETAIL",
                "leak": "🔥 CONFIDENTIAL LEAK",
                "gta 6": "🎮 GTA 6",
                "rockstar": "⭐ Rockstar"
            };

            for (let [word, replaceWith] of Object.entries(boostWords)) {
                let regex = new RegExp(word, "gi");
                formattedText = formattedText.replace(regex, replaceWith);
            }

            // Copy Action
            if (navigator.clipboard) {
                navigator.clipboard.writeText(formattedText).then(function () {
                    triggerCopySuccess();
                }).catch(function () {
                    fallbackCopy(formattedText);
                });
            } else {
                fallbackCopy(formattedText);
            }
        }

        function triggerCopySuccess() {
            var btn = document.getElementById("copyBtnText");
            if (btn) {
                btn.innerText = "🟢 Copied with Strategy Matrix! ✓";
                btn.classList.add("copied");

                // Tech sound effect logic
                try {
                    let audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    let oscillator = audioCtx.createOscillator();
                    let gainNode = audioCtx.createGain();
                    oscillator.connect(gainNode);
                    gainNode.connect(audioCtx.destination);
                    oscillator.type = 'sine';
                    oscillator.frequency.setValueAtTime(800, audioCtx.currentTime);
                    gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);
                    oscillator.start();
                    oscillator.stop(audioCtx.currentTime + 0.1);
                } catch(e) {}

                setTimeout(function () {
                    btn.innerText = "📋 Copy Strategy Data";
                    btn.classList.remove("copied");
                }, 2000);
            }
        }

        function fallbackCopy(text) {
            var textArea = document.createElement("textarea");
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand("copy");
            document.body.removeChild(textArea);
            triggerCopySuccess();
        }


        function safeText(value) {
            return String(value || "").replace(/[&<>"']/g, function(c){ return ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]); });
        }

        function saveCreatorMemory() {
            try {
                const topic = document.querySelector('input[name="topic"]');
                const type = document.querySelector('input[name="content_type"]:checked');
                if (!topic || !topic.value.trim()) return;
                const history = JSON.parse(localStorage.getItem("hookspike_history") || "[]");
                const item = { topic: topic.value.trim(), type: type ? type.value : "hooks", at: Date.now() };
                const filtered = history.filter(x => !(x.topic === item.topic && x.type === item.type));
                filtered.unshift(item);
                localStorage.setItem("hookspike_history", JSON.stringify(filtered.slice(0,20)));
            } catch(e) {}
        }

        function openStudioPanel(id) {
            document.querySelectorAll('.tool-panel').forEach(x => x.classList.remove('show'));
            const el = document.getElementById(id);
            if (el) el.classList.add('show');
            if (el) el.scrollIntoView({behavior:'smooth', block:'nearest'});
            renderHistory();
        }

        function setTopicAndType(type) {
            const topic = document.querySelector('input[name="topic"]');
            const radio = document.querySelector('input[name="content_type"][value="'+type+'"]');
            if (radio) radio.checked = true;
            if (topic) topic.focus();
        }

        async function runStudioAction(endpoint, payload, outputId, button) {
            const old = button.innerText;
            button.disabled = true;
            button.innerText = "⏳ Working...";
            const output = document.getElementById(outputId);
            if (output) { output.style.display = "block"; output.innerText = "✨ HookSpike is working..."; }
            try {
                const res = await fetch(endpoint, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
                const data = await res.json();
                if (output) output.innerText = data.ok ? (data.text || data.result || "Done.") : (data.error || "⚠️ Something went wrong.");
            } catch(e) {
                if (output) output.innerText = "⚠️ Tool is temporarily unavailable. Please try again.";
            } finally { button.disabled = false; button.innerText = old; }
        }

        function currentResultText() {
            const el = document.getElementById('rawText');
            return el ? (el.innerText || el.textContent || '').trim() : '';
        }

        function runRefine(action) {
            const topic = document.querySelector('input[name="topic"]');
            const output = currentResultText();
            const btn = document.activeElement || document.body;
            runStudioAction('/refine-content', {topic: topic ? topic.value : '', content: output, action: action, brand_voice: localStorage.getItem('hookspike_brand_voice') || ''}, 'refineOutput', btn);
        }

        function runPack() {
            const topic = document.querySelector('input[name="topic"]');
            if (!topic || !topic.value.trim()) { topic && topic.focus(); return; }
            runStudioAction('/generate-pack', {topic: topic.value, brand_voice: localStorage.getItem('hookspike_brand_voice') || ''}, 'packOutput', document.getElementById('packBtn'));
        }

        function runAnalyzer() {
            const input = document.getElementById('hookAnalyzerInput');
            const topic = document.querySelector('input[name="topic"]');
            const btn = document.getElementById('analyzeBtn');
            runStudioAction('/analyze-hook', {hook: input ? input.value : '', topic: topic ? topic.value : ''}, 'analyzerOutput', btn);
        }

        function runDiscover() {
            const category = document.getElementById('discoverCategory');
            const btn = document.getElementById('discoverBtn');
            runStudioAction('/discover-topics', {category: category ? category.value : 'general'}, 'discoverOutput', btn);
        }

        function saveBrandVoice() {
            const value = document.getElementById('brandVoice').value.trim();
            localStorage.setItem('hookspike_brand_voice', value);
            document.getElementById('brandSaved').innerText = value ? '✅ Brand voice saved on this device.' : 'ℹ️ Brand voice cleared.';
        }

        function loadBrandVoice() {
            try { const v = localStorage.getItem('hookspike_brand_voice') || ''; const el=document.getElementById('brandVoice'); if(el) el.value=v; } catch(e){}
        }

        function renderHistory() {
            const box = document.getElementById('historyList');
            if (!box) return;
            try {
                const history = JSON.parse(localStorage.getItem('hookspike_history') || '[]');
                box.innerHTML = history.length ? history.map(x => `<div class="history-item" onclick="useHistory(${JSON.stringify(x.topic).replace(/</g,'\\u003c')},${JSON.stringify(x.type)})">${safeText(x.type.toUpperCase())} • ${safeText(x.topic)}</div>`).join('') : '<div class="history-item">No saved topics yet. Your generated topics will appear here.</div>';
            } catch(e) { box.innerHTML = '<div class="history-item">History unavailable.</div>'; }
        }

        function useHistory(topic, type) {
            const input=document.querySelector('input[name="topic"]'); if(input) input.value=topic;
            const radio=document.querySelector('input[name="content_type"][value="'+type+'"]'); if(radio) radio.checked=true;
            window.scrollTo({top:0,behavior:'smooth'});
        }

        document.addEventListener('DOMContentLoaded', function(){
            loadBrandVoice(); renderHistory();
            const form=document.querySelector('form[action="/"]');
            if(form) form.addEventListener('submit', function(){
                saveCreatorMemory();
                try { const v=localStorage.getItem('hookspike_brand_voice')||''; const h=document.getElementById('brandVoiceHidden'); if(h) h.value=v; } catch(e) {}
            });
        });


    </script>

</head>


<body>

<div class="container">

    <div class="logo">
        Hook<span>Spike</span> AI ⚡
    </div>

    <p class="tagline">
        Hyper-Growth Retention Suite
    </p>


    {% if not logged_in %}

        <div class="login-box">

            <h3
                style="
                    color:#66fcf1;
                    margin-bottom:20px;
                "
            >
                Welcome Back Creator!
            </h3>

            <p
                style="
                    color:#9ca3af;
                    font-size:14px;
                    margin-bottom:30px;
                "
            >
                Sign in with Google to sync
                your tokens securely across
                all devices.
            </p>

            <a
                href="/login/google"
                class="google-btn"
            >

                <span class="google-icon">
                    G
                </span>

                <span>
                    Continue with Google
                </span>

            </a>

        </div>


    {% else %}

        <div class="user-profile">

            👤 {{ user_email }}

            |

            <a
                href="/logout"
                class="logout-link"
            >
                Logout
            </a>

        </div>


        <div class="counter-badge">

            ⚡ Neural Tokens Remaining:
            {{ tokens_left }} / 5

        </div>


        {% if show_paywall %}

            <div class="paywall-box">

                <h2>
                    🔒 Commercial Pipeline Locked
                </h2>

                <p class="pay-desc">
                    Your trial parameters have expired. Select an enterprise tier below to lift engine execution rate-limits instantly.
                </p>

                <div class="pricing-plan">

                    <!-- Plan 1: Pro Suite -->
                    <div class="plan-card">
                        <h4>Creator Pro Plan</h4>
                        <p class="plan-sub">Perfect for rising independent streamers & video editors</p>
                        <div class="plan-price-row">
                            <p class="price">₹1,499</p>
                            <span class="duration">/ monthly subscription</span>
                        </div>
                    </div>

                    <!-- Plan 2: Agency Suite (Popular) -->
                    <div class="plan-card popular">
                        <div class="plan-badge">Most Popular</div>
                        <h4>Agency Growth Suite</h4>
                        <p class="plan-sub">Full speed access with multi-platform deep tracking vectors</p>
                        <div class="plan-price-row">
                            <p class="price">₹1,999</p>
                            <span class="duration">/ monthly subscription</span>
                        </div>
                    </div>

                </div>

                <div class="upi-details">
                    <span>💥 Merchant UPI Anchor:</span>
                    <span style="color: #fff; font-family: monospace;">9657119506@axl</span>
                </div>

                <!-- Open UPI Gateway intent string configuration mapped to professional plan pricing -->
                <a
                    href="intent://pay?pa=9657119506@axl&pn=HookSpike%20AI&am=1499&cu=INR#Intent;scheme=upi;package=com.google.android.apps.nbu.paisa.user;end"
                    class="pay-btn"
                >
                    📱 Initialize Secure Gateway Payment
                </a>

            </div>
            


        {% else %}

            <form
                method="POST"
                action="/"
                onsubmit="showLoading()"
            >

                <label>What do you want to create?</label>

                <div class="content-selector">

                    <div class="content-option">
                        <input type="radio" id="typeHooks" name="content_type" value="hooks"
                            {% if content_type == "hooks" or not content_type %}checked{% endif %} required>
                        <label for="typeHooks">
                            <span class="option-icon">🔥</span>
                            <span class="option-copy">
                                <span class="option-title">Hooks</span>
                                <span class="option-sub">Scroll-stopping hooks, arranged in a clean sequence</span>
                            </span>
                        </label>
                    </div>

                    <div class="content-option">
                        <input type="radio" id="typeScript" name="content_type" value="script"
                            {% if content_type == "script" %}checked{% endif %}>
                        <label for="typeScript">
                            <span class="option-icon">🎬</span>
                            <span class="option-copy">
                                <span class="option-title">Script</span>
                                <span class="option-sub">A topic-specific script with a strong opening and flow</span>
                            </span>
                        </label>
                    </div>

                    <div class="content-option">
                        <input type="radio" id="typeThumbnail" name="content_type" value="thumbnail"
                            {% if content_type == "thumbnail" %}checked{% endif %}>
                        <label for="typeThumbnail">
                            <span class="option-icon">🖼️</span>
                            <span class="option-copy">
                                <span class="option-title">Thumbnail</span>
                                <span class="option-sub">Thumbnail concepts plus an AI visual example</span>
                            </span>
                        </label>
                    </div>

                </div>

                <label>Enter Topic / Search:</label>

                <input type="hidden" id="brandVoiceHidden" name="brand_voice" value="">

                <input
                    type="text"
                    name="topic"
                    placeholder="Search a topic, game, update, trend, or idea..."
                    value="{{ topic }}"
                    required
                >

                <button type="submit" id="submitBtn">
                    Create My {{ content_type|title if content_type else "Hooks" }} 🚀
                </button>

            </form>

        {% endif %}



        {% if not show_paywall %}
            <div class="pack-banner">
                <strong>🚀 One Topic → Complete Creator Pack</strong>
                <span>Get titles, 7 hooks, one script, 3 thumbnail concepts, description, hashtags and keywords from one verified research pass.</span>
                <button id="packBtn" class="tool-action" type="button" onclick="runPack()" style="margin-top:12px;">✨ Build My Complete Pack</button>
                <div id="packOutput" class="tool-output" style="display:none;"></div>
            </div>

            <div class="studio-grid">
                <div class="studio-card" onclick="openStudioPanel('discoverPanel')"><div class="icon">🔥</div><strong>Fresh Topic Radar</strong><span>Find current content opportunities with web-verified research.</span></div>
                <div class="studio-card" onclick="openStudioPanel('refinePanel')"><div class="icon">✨</div><strong>Make It Better</strong><span>Remix your result for curiosity, natural tone, Shorts and more.</span></div>
                <div class="studio-card" onclick="openStudioPanel('analyzerPanel')"><div class="icon">🧲</div><strong>Hook Analyzer</strong><span>Get concrete feedback and a stronger rewrite.</span></div>
                <div class="studio-card" onclick="openStudioPanel('brandPanel')"><div class="icon">🎙️</div><strong>My Creator Voice</strong><span>Save your preferred tone on this device for future sessions.</span></div>
                <div class="studio-card" onclick="openStudioPanel('historyPanel')"><div class="icon">🗂️</div><strong>Recent Ideas</strong><span>Quickly reuse your latest topics and content modes.</span></div>
                <div class="studio-card" onclick="setTopicAndType('script')"><div class="icon">📱</div><strong>Shorts Mode</strong><span>Switch to Script and use the Shorts remix after generation.</span></div>
            </div>

            <div id="refinePanel" class="tool-panel">
                <div class="tool-title">✨ Make this result better</div>
                <div class="quick-actions">
                    <button class="quick-btn" onclick="runRefine('more-curious')">🧲 More Curiosity</button>
                    <button class="quick-btn" onclick="runRefine('more-viral')">🔥 Punchier</button>
                    <button class="quick-btn" onclick="runRefine('more-natural')">🗣️ Natural</button>
                    <button class="quick-btn" onclick="runRefine('shorter')">⚡ Shorter</button>
                    <button class="quick-btn" onclick="runRefine('cinematic')">🎬 Cinematic</button>
                    <button class="quick-btn" onclick="runRefine('shorts')">📱 Shorts</button>
                    <button class="quick-btn" onclick="runRefine('gaming')">🎮 Gaming</button>
                    <button class="quick-btn" onclick="runRefine('anime')">🍥 Anime</button>
                    <button class="quick-btn" onclick="runRefine('thumbnail-clickable')">🖼️ Thumbnail</button>
                </div>
                <div id="refineOutput" class="tool-output">Generate a result first, then choose a transformation.</div>
            </div>

            <div id="analyzerPanel" class="tool-panel">
                <div class="tool-title">🧲 Hook Analyzer</div>
                <textarea id="hookAnalyzerInput" class="tool-input" placeholder="Paste a hook here..."></textarea>
                <button id="analyzeBtn" class="tool-action" type="button" onclick="runAnalyzer()">🔍 Analyze Hook</button>
                <div id="analyzerOutput" class="tool-output">You’ll get clarity, curiosity, first-seconds impact, specificity and one improved version.</div>
            </div>

            <div id="discoverPanel" class="tool-panel">
                <div class="tool-title">🔥 Fresh Topic Radar</div>
                <select id="discoverCategory" class="tool-select">
                    <option value="general">🌐 General Creator Trends</option>
                    <option value="gaming">🎮 Gaming</option>
                    <option value="anime">🍥 Anime</option>
                    <option value="tech">🤖 Tech & AI</option>
                    <option value="movies">🎬 Movies & Entertainment</option>
                    <option value="sports">⚽ Sports</option>
                </select>
                <button id="discoverBtn" class="tool-action" type="button" onclick="runDiscover()">🔎 Find Current Topics</button>
                <div id="discoverOutput" class="tool-output">Fresh ideas will appear here.</div>
            </div>

            <div id="brandPanel" class="tool-panel">
                <div class="tool-title">🎙️ My Creator Voice</div>
                <textarea id="brandVoice" class="tool-input" placeholder="Example: Hinglish, energetic, short sentences, gaming audience, no corporate wording..."></textarea>
                <button class="tool-action" type="button" onclick="saveBrandVoice()">💾 Save My Style</button>
                <div id="brandSaved" class="tool-output">Saved locally on this device. We keep your existing backend unchanged.</div>
            </div>

            <div id="historyPanel" class="tool-panel">
                <div class="tool-title">🗂️ Recent Ideas</div>
                <div id="historyList" class="history-list"></div>
            </div>
        {% endif %}

        <div
            id="loaderIcon"
            class="loader"
        ></div>

        <div
            id="loaderText"
            class="loading-text"
        >
            ⚡ HookSpike Compiling
            Multi-Platform Vectors...
        </div>


        {% if result_text and not show_paywall %}

            <div class="result-box">

                <div class="result-header">
                    <h3 style="margin:0;">
                        {% if content_type == "hooks" %}🔥 Hook Lab
                        {% elif content_type == "script" %}🎬 Script Studio
                        {% else %}🖼️ Thumbnail Lab
                        {% endif %}
                    </h3>
                    <span class="result-type">{{ content_type|title }}</span>
                </div>

                <div class="hook-card">
                    <div id="rawText">{{ result_text }}</div>

                    {% if content_type == "thumbnail" %}
                        <div id="generatedImageBox"></div>
                        <button
                            id="generateImageBtn"
                            class="generate-image-btn"
                            type="button"
                            onclick="generateThumbnailImage()"
                        >
                            🖼️ Generate Image for an Idea
                        </button>
                        <div id="imageStatus" class="image-status">
                            💡 Want to see the concept? Tap the button above to generate an example image.
                        </div>
                    {% endif %}

                    {% if content_type == "hooks" %}
                        <div class="research-note">
                            ⚡ Hooks are arranged in sequence so you can test different opening angles
                            without scripts or thumbnail concepts mixed into the result.
                        </div>
                    {% elif content_type == "script" %}
                        <div class="research-note">
                            🎬 This result is focused only on the searched topic, with current facts checked when required.
                        </div>
                    {% else %}
                        <div class="research-note">
                            🎨 The text defines the thumbnail direction; the generated visual is an example concept.
                        </div>
                    {% endif %}
                </div>

                <button id="copyBtnText" class="copy-btn" onclick="copyText()" type="button">
                    📋 Copy Result
                </button>

            </div>

        {% endif %}

    {% endif %}

</div>

</body>

</html>
"""


# ============================================================
# TOKEN FUNCTIONS
# ============================================================

def get_user_tokens(user_id, email):

    # Development fallback if Supabase is unavailable.
    if not supabase:
        return 5

    try:

        res = (
            supabase
            .table("user_tokens")
            .select("tokens_left")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        if res.data:

            return int(
                res.data[0]["tokens_left"]
            )

        # First login -> create token record
        supabase.table("user_tokens").insert(
            {
                "id": user_id,
                "email": email,
                "tokens_left": 5,
            }
        ).execute()

        return 5

    except Exception as e:

        print(
            f"Database error in get_user_tokens: {e}"
        )

        return 5


def decrease_user_token(user_id):

    if not supabase:
        return

    try:

        res = (
            supabase
            .table("user_tokens")
            .select("tokens_left")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        if not res.data:
            return

        # FIX:
        # res.data is a list.
        current = int(
            res.data[0]["tokens_left"]
        )

        if current <= 0:
            return

        (
            supabase
            .table("user_tokens")
            .update(
                {
                    "tokens_left": current - 1
                }
            )
            .eq("id", user_id)
            .execute()
        )

    except Exception as e:

        print(
            f"Database error on token update: {e}"
        )


# ============================================================
# AI RESULT / TOKEN SAFETY
# ============================================================

def _ai_result_is_success(result):
    """
    Only consume a user token when the AI engine actually returned
    a usable result. Provider/configuration failures must not burn tokens.
    """
    if not isinstance(result, str):
        return bool(result)

    text = result.strip().lower()

    failure_markers = (
        "⚠️ ai is temporarily unavailable",
        "⚠️ ai is temporarily busy",
        "ai api key is not configured",
        "gemini api key is not configured",
        "openai api key is not configured",
        "openai sdk is missing",
        "gemini research failed",
        "openai creative generation failed",
    )

    return bool(text) and not any(marker in text for marker in failure_markers)


# ============================================================
# HOME
# ============================================================

@app.route("/", methods=["GET", "POST"])
def index():

    # IMPORTANT:
    # OAuth callback saves these values.
    # We don't process ?code= here anymore.
    user_id = session.get("user_id")
    email = session.get("user_email")

    # Not logged in
    if not user_id:

        return render_template_string(
            HTML_TEMPLATE,
            logged_in=False,
        )


    # Get current token count
    tokens_left = get_user_tokens(
        user_id,
        email,
    )

    result = None
    result_text = None
    result_image = None
    content_type = "hooks"
    topic = ""

    show_paywall = (
        tokens_left <= 0
    )


    # ========================================================
    # AI GENERATION
    # ========================================================

    if request.method == "POST":

        content_type = (
            request.form
            .get("content_type", "hooks")
            .strip()
            .lower()
        )

        if content_type not in {"hooks", "script", "thumbnail"}:
            content_type = "hooks"

        topic = (
            request.form
            .get("topic", "")
            .strip()
        )

        brand_voice = (
            request.form
            .get("brand_voice", "")
            .strip()
        )


        if not topic:

            return render_template_string(
                HTML_TEMPLATE,
                logged_in=True,
                user_email=email,
                result=None,
                result_text=None,
                result_image=None,
                content_type=content_type,
                topic="",
                tokens_left=tokens_left,
                show_paywall=show_paywall,
            )


        if tokens_left > 0:

            started_at = time.perf_counter()

            try:

                result = get_ai_response(
                    content_type,
                    topic,
                    brand_voice=brand_voice[:4000],
                )

                elapsed = time.perf_counter() - started_at

                print(
                    f"AI request completed in {elapsed:.2f}s "
                    f"| content_type={content_type} "
                    f"| topic_chars={len(topic)}"
                )

                # New engine returns text plus an optional thumbnail image.
                if isinstance(result, dict):
                    result_text = result.get("text")
                    result_image = result.get("image")
                else:
                    result_text = result
                    result_image = None

                # IMPORTANT:
                # Do NOT consume a token when the AI provider failed.
                if _ai_result_is_success(result):
                    decrease_user_token(user_id)

                    tokens_left = get_user_tokens(
                        user_id,
                        email,
                    )
                else:
                    print(
                        "AI request did not produce a successful result; "
                        "token was not consumed."
                    )

            except Exception as e:

                elapsed = time.perf_counter() - started_at

                print(
                    f"AI Engine Error after {elapsed:.2f}s: "
                    f"{repr(e)}"
                )

                result = (
                    "⚠️ AI Engine temporarily unavailable. "
                    "Your token was not consumed. Please try again."
                )


        show_paywall = (
            tokens_left <= 0
        )


    return render_template_string(
        HTML_TEMPLATE,
        logged_in=True,
        user_email=email,
        result=result,
        result_text=result_text,
        result_image=result_image,
        content_type=content_type,
        topic=topic,
        tokens_left=tokens_left,
        show_paywall=show_paywall,
    )


# ============================================================
# GOOGLE LOGIN
# ============================================================

@app.route("/login/google")
def login_google():

    if not supabase:

        return (
            "Supabase connection error. "
            "Check Render environment variables.",
            500,
        )


    # THIS MUST MATCH SUPABASE REDIRECT URL
    redirect_url = (
        "https://hookspike-core.onrender.com"
        "/auth/callback"
    )


    try:

        response = (
            supabase
            .auth
            .sign_in_with_oauth(
                {
                    "provider": "google",

                    "options": {
                        "redirect_to": redirect_url,
                    },
                }
            )
        )

        return redirect(
            response.url
        )

    except Exception as e:

        print(
            f"Google OAuth start error: {e}"
        )

        return (
            "Google login could not be started. "
            "Please try again.",
            500,
        )


# ============================================================
# GOOGLE OAUTH CALLBACK
# ============================================================

@app.route("/auth/callback")
def auth_callback():

    code = request.args.get("code")

    error = request.args.get("error")

    error_description = request.args.get(
        "error_description"
    )


    # --------------------------------------------------------
    # Google/Supabase returned an OAuth error
    # --------------------------------------------------------

    if error:

        print(
            "OAuth error:",
            error,
            error_description,
        )

        session.clear()

        return (
            "Google login was cancelled or rejected. "
            "Please start again.",
            400,
        )


    # --------------------------------------------------------
    # No authorization code
    # --------------------------------------------------------

    if not code:

        print(
            "OAuth callback received "
            "without authorization code."
        )

        session.clear()

        return (
            "Login callback did not contain "
            "an authorization code.",
            400,
        )


    if not supabase:

        return (
            "Supabase connection error.",
            500,
        )


    try:

        # ----------------------------------------------------
        # Exchange the PKCE authorization code
        # ----------------------------------------------------

        response = (
            supabase
            .auth
            .exchange_code_for_session(
                {
                    "auth_code": code
                }
            )
        )


        if not response:

            raise RuntimeError(
                "Supabase returned an empty response."
            )


        # ----------------------------------------------------
        # Get the authenticated user from the new session
        # ----------------------------------------------------

        user_response = (
            supabase
            .auth
            .get_user()
        )


        user = getattr(
            user_response,
            "user",
            None,
        )


        if not user:

            raise RuntimeError(
                "Could not retrieve authenticated user."
            )


        # ----------------------------------------------------
        # Save only the required identity in Flask session
        # ----------------------------------------------------

        session["user_id"] = user.id

        session["user_email"] = (
            user.email or ""
        )

        session.permanent = True

        print(
            "Google login successful:",
            user.email,
        )


        # ----------------------------------------------------
        # IMPORTANT:
        # Redirect to / WITHOUT the OAuth code.
        # This prevents the login-loop.
        # ----------------------------------------------------

        return redirect(
            url_for("index")
        )


    except Exception as e:

        print(
            "OAuth callback exchange error:",
            repr(e),
        )

        # Remove incomplete login state
        session.clear()

        return (
            "Google login failed. "
            "Please start a fresh login attempt.",
            400,
        )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    try:

        if supabase:

            supabase.auth.sign_out()

    except Exception as e:

        print(
            f"Supabase logout error: {e}"
        )

    finally:

        # Always clear Flask session
        session.clear()


    return redirect(
        url_for("index")
    )


# ============================================================
# CREATOR STUDIO ROUTES
# ============================================================

def _studio_token_allowed():
    user_id = session.get("user_id")
    email = session.get("user_email", "")
    if not user_id:
        return None, 401, {"ok": False, "error": "⚠️ Please log in first."}
    tokens = get_user_tokens(user_id, email)
    if tokens <= 0:
        return None, 402, {"ok": False, "error": "🔒 You are out of creator tokens. Please add more tokens to continue."}
    return (user_id, email), 200, None


def _studio_finish(user_id, email, result):
    if result:
        decrease_user_token(user_id)
        return get_user_tokens(user_id, email)
    return get_user_tokens(user_id, email)


@app.route("/generate-pack", methods=["POST"])
def generate_pack_route():
    identity, status, error = _studio_token_allowed()
    if error:
        return jsonify(error), status
    user_id, email = identity
    try:
        data = request.get_json(silent=True) or {}
        topic = str(data.get("topic", "")).strip()
        if not topic:
            return jsonify({"ok": False, "error": "⚠️ Please enter a topic first."}), 400
        result, err = generate_creator_pack(topic, str(data.get("brand_voice", ""))[:4000])
        if not result:
            return jsonify({"ok": False, "error": "⚠️ Creator pack is temporarily unavailable. Please try again."}), 200
        _studio_finish(user_id, email, result)
        return jsonify({"ok": True, "text": result})
    except Exception as exc:
        print(f"Creator pack route error: {repr(exc)}")
        return jsonify({"ok": False, "error": "⚠️ Creator pack is temporarily unavailable."}), 200


@app.route("/refine-content", methods=["POST"])
def refine_content_route():
    identity, status, error = _studio_token_allowed()
    if error:
        return jsonify(error), status
    user_id, email = identity
    try:
        data = request.get_json(silent=True) or {}
        result, err = refine_creator_content(
            topic=str(data.get("topic", "")),
            content=str(data.get("content", "")),
            action=str(data.get("action", "")),
            brand_voice=str(data.get("brand_voice", ""))[:4000],
        )
        if not result:
            return jsonify({"ok": False, "error": "⚠️ This improvement is temporarily unavailable. Please try again."}), 200
        _studio_finish(user_id, email, result)
        return jsonify({"ok": True, "text": result})
    except Exception as exc:
        print(f"Refine route error: {repr(exc)}")
        return jsonify({"ok": False, "error": "⚠️ Improvement tool is temporarily unavailable."}), 200


@app.route("/analyze-hook", methods=["POST"])
def analyze_hook_route():
    identity, status, error = _studio_token_allowed()
    if error:
        return jsonify(error), status
    user_id, email = identity
    try:
        data = request.get_json(silent=True) or {}
        result, err = analyze_hook(
            hook=str(data.get("hook", "")),
            topic=str(data.get("topic", "")),
        )
        if not result:
            return jsonify({"ok": False, "error": "⚠️ Hook analysis is temporarily unavailable."}), 200
        _studio_finish(user_id, email, result)
        return jsonify({"ok": True, "text": result})
    except Exception as exc:
        print(f"Hook analyzer route error: {repr(exc)}")
        return jsonify({"ok": False, "error": "⚠️ Hook analyzer is temporarily unavailable."}), 200


@app.route("/discover-topics", methods=["POST"])
def discover_topics_route():
    identity, status, error = _studio_token_allowed()
    if error:
        return jsonify(error), status
    user_id, email = identity
    try:
        data = request.get_json(silent=True) or {}
        result, err = discover_topics(str(data.get("category", "general")))
        if not result:
            return jsonify({"ok": False, "error": "⚠️ Topic radar is temporarily unavailable."}), 200
        _studio_finish(user_id, email, result)
        return jsonify({"ok": True, "text": result})
    except Exception as exc:
        print(f"Topic discovery route error: {repr(exc)}")
        return jsonify({"ok": False, "error": "⚠️ Topic radar is temporarily unavailable."}), 200


# ============================================================
# ON-DEMAND THUMBNAIL IMAGE
# ============================================================

@app.route("/generate-thumbnail", methods=["POST"])
def generate_thumbnail_route():

    if not session.get("user_id"):
        return jsonify({
            "ok": False,
            "image": None,
            "error": "⚠️ Please log in first."
        }), 401

    try:
        data = request.get_json(silent=True) or {}
        topic = str(data.get("topic", "")).strip()
        thumbnail_text = str(data.get("thumbnail_text", "")).strip()

        if not topic or not thumbnail_text:
            return jsonify({
                "ok": False,
                "image": None,
                "error": "⚠️ Thumbnail details are missing. Please generate the thumbnail concepts again."
            }), 400

        result = generate_thumbnail_image(
            topic=topic[:12000],
            thumbnail_text=thumbnail_text[:30000],
        )

        return jsonify(result)

    except Exception as exc:
        print(f"On-demand thumbnail route error: {repr(exc)}")
        return jsonify({
            "ok": False,
            "image": None,
            "error": "⚠️ Image server is busy — thumbnail image can't be generated right now."
        }), 200


# ============================================================
# HEALTH CHECK
# ============================================================

@app.after_request
def add_no_cache_headers(response):
    # AI results are dynamic; never let an intermediary/browser serve
    # an old generated page as a new result.
    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/favicon.png")
def favicon():
    return send_file(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "file_00000000fd8481fab2b4f371e41aa854.png"
        ),
        mimetype="image/png"
        )
@app.route("/health")
def health():

    return {
        "status": "ok",
        "app": "HookSpike AI",
        "ai_engine": "v2",
    }


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000,
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
    )

