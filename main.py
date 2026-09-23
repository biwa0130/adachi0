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

# --- ぐちゃぐちゃマルコフ連鎖 ＋ 10%絵文字トッピング関数 ---
def generate_text():
    try:
        if os.path.exists('tweets_data.txt'):
            with open('tweets_data.txt', 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            
            if lines:
                tagger = MeCab.Tagger(unidic_lite.DICDIR)
                model = {}
                
                for line in lines:
                    parsed = tagger.parse(line)
                    words = []
                    for row in parsed.split('\n'):
                        if row == 'EOS' or row == '':
                            continue
                        cols = row.split('\t')
                        if len(cols) > 0:
                            words.append(cols[0])
                    
                    if len(words) < 2:
                        continue
                    
                    for i in range(len(words) - 1):
                        w1, w2 = words[i], words[i+1]
                        if w1 not in model:
                            model[w1] = []
                        model[w1].append(w2)
                
                if model:
                    current_w = random.choice(list(model.keys()))
                    generated_words = [current_w]
                    
                    length = random.randint(3, 18)
                    for _ in range(length):
                        if current_w in model:
                            next_w = random.choice(model[current_w])
                            generated_words.append(next_w)
                            current_w = next_w
                            if random.random() < 0.15:
                                break
                        else:
                            break
                    
                    result_text = "".join(generated_words)
                    
                    # わけわからん絵文字の候補
                    emojis = ["🫠", "✨", "💀", "👍", "🤔", "🥺", "草", "🙏", "🌿", "💡"]
                    
                    # 10% (0.1) の確率で絵文字をぶっこむ
                    if random.random() < 0.1:
                        chosen_emoji = random.choice(emojis)
                        # 50%の確率で「先頭」か「文末」にランダム配置
                        if random.random() < 0.5:
                            result_text = chosen_emoji + " " + result_text
                        else:
                            result_text = result_text + " " + chosen_emoji
                    
                    if len(result_text) > 1:
                        print(f"ぐちゃぐちゃ生成成功: {result_text}")
                        return result_text

                return random.choice(lines)
                
        return "トイレットペーパー切れた🫠"
        
    except Exception as e:
        print(f"Generation Error: {e}")
        return "悲報：おえ〜💀"

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
    
    # 反応させるキーワードリスト（固有ワード ＋ 足立レイのカラーコード）
    keywords = [
        "足立レイ", "レイ", "からあげ", "ズモ", "ずも", "生殖器",
        "#FF6600", "#FF7F00", "#FFFFFF", "#333333", "#4D4D4D", "#FFCC00", "#FF9900",
        "FF6600", "FF7F00", "FFFFFF", "333333", "4D4D4D", "FFCC00", "FF9900"
    ]
    
    if any(keyword in user_msg for keyword in keywords):
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
    while True:
        schedule.run_pending()
        time.sleep(60)

# --- サーバー起動 ---
if __name__ == "__main__":
    t = threading.Thread(target=run_schedule)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
