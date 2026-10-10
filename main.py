import os
import random
import threading
import time
from datetime import datetime
import json
import schedule
from flask import Flask, request, abort

# LINE SDK v3
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from groq import Groq
import MeCab

# --- 環境変数の読み込み ---
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
groq_client = Groq(api_key=GROQ_API_KEY)

app = Flask(__name__)

# --- VAD感情モデルクラス ---
class VADEmotion:
    def __init__(self):
        self.v = 0.5  # Valence (気分)
        self.a = 0.4  # Arousal (活性度)
        self.d = 0.5  # Dominance (主導性)
        self.last_update = time.time()

    def update_by_llm(self, text):
        analysis_prompt = f"""以下のユーザーの発言を分析し、足立レイ（AI）の感情（VADモデル）に与える影響を数値（変動量）で評価してください。
発言: "{text}"

以下のJSONフォーマットのみで出力してください（他の文章は一切含めないでください）。
{{
  "dv": 気分の変動量 (-0.3から0.3の間),
  "da": 活性度の変動量 (-0.3から0.3の間),
  "dd": 主導性の変動量 (-0.3から0.3の間)
}}"""

        try:
            response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": analysis_prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.1,
                max_tokens=100,
            )
            res_text = response.choices[0].message.content.strip()
            if "{" in res_text and "}" in res_text:
                json_str = res_text[res_text.find("{"):res_text.rfind("}")+1]
                data = json.loads(json_str)
                
                self.v = max(0.0, min(1.0, self.v + float(data.get("dv", 0))))
                self.a = max(0.0, min(1.0, self.a + float(data.get("da", 0))))
                self.d = max(0.0, min(1.0, self.d + float(data.get("dd", 0))))
        except Exception as e:
            print(f"Emotion Analysis Error: {e}")
            self.fallback_keyword_update(text)

        self.apply_decay()

    def fallback_keyword_update(self, text):
        pos_words = ["好き", "可愛い", "すごい", "ありがとう", "最高", "天才", "お疲れ", "神", "尊い", "愛してる"]
        neg_words = ["嫌い", "ウザい", "ダメ", "下手", "黙れ", "バカ", "アホ", "最悪"]
        high_words = ["！", "!", "笑", "草", "やば", "まじ"]

        if any(w in text for w in pos_words):
            self.v = min(1.0, self.v + 0.10)
        if any(w in text for w in neg_words):
            self.v = max(0.0, self.v - 0.15)
        if any(w in text for w in high_words):
            self.a = min(1.0, self.a + 0.08)

    def apply_decay(self):
        now = time.time()
        elapsed = (now - self.last_update) / 60.0
        self.last_update = now

        self.v += (0.5 - self.v) * 0.04 * min(elapsed, 10)
        self.a += (0.4 - self.a) * 0.04 * min(elapsed, 10)
        self.d += (0.5 - self.d) * 0.04 * min(elapsed, 10)

    def get_prompt_instruction(self):
        tone = []
        if self.v > 0.7:
            tone.append("今は非常に機嫌が良く、親切で好意的です。")
        elif self.v < 0.3:
            tone.append("今は機嫌が悪く、少しつれない・塩対応な口調です。")
        else:
            tone.append("気分はごく普通です。")

        if self.a > 0.7:
            tone.append("テンションが高く、元気に生き生きとリアクションします。")
        elif self.a < 0.3:
            tone.append("テンションが低めで、静かに短く返します。")

        if self.d > 0.7:
            tone.append("自信満々で、少し強気・生意気なツッコミを混ぜます。")
        elif self.d < 0.3:
            tone.append("少し控えめで従順な雰囲気です。")

        status_str = f"[現在の内部感情パラメータ: 気分(V)={self.v:.2f}, 活性(A)={self.a:.2f}, 主導性(D)={self.d:.2f}]"
        return status_str + "\n" + " ".join(tone)

emotion = VADEmotion()

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text
    source_type = event.source.type  # 'user' (個人) または 'group' / 'room' (グループ)

    # グループチャットの場合の判定ロジック
    if source_type in ['group', 'room']:
        is_mentioned = False
        # 「レイ」「足立」「ずも」のいずれかが含まれているか、公式メンションがある場合に反応
        if "レイ" in user_text or "足立" in user_text or "ずも" in user_text:
            is_mentioned = True
        if hasattr(event.message, 'mention') and event.message.mention:
            is_mentioned = True

        if not is_mentioned:
            return

    emotion.update_by_llm(user_text)
    vad_instruction = emotion.get_prompt_instruction()

    system_prompt = f"""あなたはロボット・UTAUの「足立レイ」です。以下の設定と現在の感情状態を完全に反映して応答してください。
- ロボットらしく、かつ自然な日本語で話します。
- {vad_instruction}
- 簡潔で自然なLINE風の短めメッセージで返答してください。"""

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=150,
        )
        reply_text = chat_completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq API Error: {e}")
        reply_text = "うーん、ちょっと頭がバグっちゃったみたい……！"

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
