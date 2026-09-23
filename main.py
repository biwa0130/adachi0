import os
import random
import threading
import time
import MeCab
import unidic_lite
import schedule
from flask import Flask, request, abort

# LINE SDK v3
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, PushMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)

# --- 環境変数の取得 ---
CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
GROUP_ID = os.environ.get('LINE_GROUP_ID')

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# --- 文章生成 & MeCabテスト関数（UniDic版） ---
def generate_text():
    try:
        # unidic-lite の辞書パスを自動で読み込ませる
        tagger = MeCab.Tagger(unidic_lite.DICDIR)
        
        # 動作確認用
        sample_parse = tagger.parse("足立レイが起動したよ")
        print(f"MeCab (UniDic) 動作確認OK: {sample_parse.strip()}")

        # tweets_data.txt からセリフを読み込む
        if os.path.exists('tweets_data.txt'):
            with open('tweets_data.txt', 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            if lines:
                return random.choice(lines)
                
        # ファイルがない場合の予備テキスト
        return "足立レイだよ！よろしくね。"
        
    except Exception as e:
        print(f"MeCab / UniDic Error: {e}")
        return "あれっ、MeCabの初期化でエラーが出ちゃったみたい……。"

# --- LINE Webhook 受信ルート ---
@app.route("/")
def hello():
    return "Adachi Rei Server is LIVE!"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# --- メッセージを受け取ったときの処理 ---
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_msg = event.message.text
    if "足立レイ" in user_msg or "レイ" in user_msg:
        reply_text = generate_text()
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )

# --- 9時〜20時のランダム自動投稿 ---
def scheduled_job():
    if not GROUP_ID:
        print("GROUP_IDが設定されていません")
        return
        
    push_text = generate_text()
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.push_message(
            PushMessageRequest(
                to=GROUP_ID,
                messages=[TextMessage(text=push_text)]
            )
        )
    print(f"自動投稿しました: {push_text}")
    set_random_schedule()

def set_random_schedule():
    schedule.clear()
    random_hour = random.randint(9, 19)
    random_minute = random.randint(0, 59)
    time_str = f"{random_hour:02d}:{random_minute:02d}"
    
    schedule.every().day.at(time_str).do(scheduled_job)
    print(f"次の自動投稿は {time_str} にセットされました")

def run_schedule():
    set_random_schedule()
    while Time.sleep(60):
        schedule.run_pending()
        time.sleep(60)

# --- サーバー起動 ---
if __name__ == "__main__":
    t = threading.Thread(target=run_schedule)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
