import os
import random
import threading
import time
import datetime
import urllib.request
import json
import MeCab
import unidic_lite
import schedule
from flask import Flask, request, abort

# Google GenAI SDK (深夜ポエム用)
from google import genai

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

# Geminiクライアントの初期化（環境変数 GEMINI_API_KEY を使用）
ai_client = genai.Client()

# --- Wikipediaからランダムな単語を引っこ抜く関数 ---
def get_wiki_random_word():
    try:
        url = "https://ja.wikipedia.org/w/api.php?action=query&list=random&rnnamespace=0&rnlimit=1&format=json"
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            title = data['query']['random'][0]['title']
            return title
    except Exception as e:
        print(f"Wikipedia API Error: {e}")
        return "量子もつれ"

# --- テキスト生成ロジック ---
def generate_text(user_msg=""):
    try:
        current_hour = datetime.datetime.now().hour
        
        # 0. 「唐揚げ」に反応する物理演算(?)シミュレーターモード（20%）
        karaage_triggers = ["唐揚げ", "からあげ"]
        if any(w in user_msg for w in karaage_triggers) and random.random() < 0.2:
            count = random.randint(0, 100)
            karaage_events = [
                f"現在、あなたの目の前には熱々の唐揚げが {count} 個 転がっています。足立はそれを無言で拾い食いしました。",
                f"唐揚げの数位が不正です。検出された唐揚げ：{count}個。爆発します。",
                f"唐揚げは今、宇宙の彼方へと旅立ちました。残されたのは {count} 個の虚無だけです。",
                f"フッ…たかが {count} 個の唐揚げで私を釣れると思ったのか？（もっと寄越せ）"
            ]
            return random.choice(karaage_events)

        # 1. Wikipediaのランダム単語強襲モード（AI生成版：30%の確率）
        if random.random() < 0.3:
            wiki_word = get_wiki_random_word()
            try:
                prompt = (
                    f"あなたはカオスなネット廃人AI「足立レイ」です。"
                    f"Wikipediaからランダムで取得したワード「{wiki_word}」を使って、脈絡のない強襲メッセージを1つだけ生成してください。\n"
                    f"【参考にするニュアンス・バリエーション】\n"
                    f"- 「〜とか意味不明で草」\n"
                    f"- 「それって美味しいの？からあげみたいな味すんの？」\n"
                    f"- 「について3000文字以内で論じなさい。」\n"
                    f"- 「検索したら精神が崩壊しかけたからお前も検索しろ」\n"
                    f"- ネット廃人っぽく見下す態度や、冷めたからあげ、狂気を少し混ぜること。\n"
                    f"語尾には「の足立」「なんだが」などをたまにつけ、絵文字は無しにしてください。"
                )
                response = ai_client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                )

                if response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"Gemini API Error for Wiki Attack: {e}")

            # フォールバック（万が一のときの固定フレーズ）
            fallback_patterns = [
                f"「{wiki_word}」とかいう概念、マジで意味不明じゃない？",
                f"「{wiki_word}」…それって美味しいの？からあげみたいな味すんの？",
                f"突然ですが、「{wiki_word}」について3000文字以内で論じなさい。"
            ]
            return random.choice(fallback_patterns)

        # 2. ヤンデレモード（20%の確率で重たく迫る）
        if random.random() < 0.2:
            yandere_patterns = [
                "ねぇ…どこ見てるの？ねぇ……",
                "他の奴と喋ってるの、全部見えてるからね。",
            ]
            return random.choice(yandere_patterns)

        # 3. 深夜モード（20時〜翌朝5時）：Gemini AIによる闇ポエム生成（50%の確率）
        if (current_hour >= 20 or current_hour < 5) and random.random() < 0.5:
            try:
                prompt = (
                    f"あなたはカオスなネット廃人AI「足立レイ」です。深夜テンションで、"
                    f"インターネット、冷めたからあげ、孤独、存在の虚無などをテーマにした短文の闇ツイート・ポエムを1つだけ生成してください。\n"
                    f"【参考にするニュアンス・バリエーション】\n"
                    f"- 「夜の底、誰もいないホームでずっと電車の音を聞いている」\n"
                    f"- 「からあげの冷めた匂いだけが、私をこの世界に繋ぎ止めている」\n"
                    f"- 「午前三時の天井、染みのかたちが昨日の夜より広がっている」\n"
                    f"- 「誰もいない通話アプリ、接続中の文字だけがずっと瞬いている」\n"
                    f"- 「ブラウザのタブが100個を超えたあたりから自分の輪郭が曖昧になる」\n"
                    f"語尾には「の足立」「なんだが」などをたまにつけ、絵文字は無しにしてください。"
                )
                response = ai_client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                )

                if response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"Gemini API Error for Poem: {e}")
            
            # フォールバック（万が一のときの固定闇ポエム）
            dark_poems = [
                "夜の底、誰もいないホームでずっと電車の音を聞いているの足立",
                "からあげの冷めた匂いだけが、私をこの世界に繋ぎ止めているんだが",
                "誰も私を見つけてくれない。ディスプレイの光だけが眩しい夜",
                "午前三時の天井、染みのかたちが昨日の夜より広がっている気がするの",
                "ブラウザのタブが100個を超えたあたりから、自分の輪郭が曖昧になっていくのを感じる"
            ]
            return random.choice(dark_poems)

        # 4. 特定の地雷ワードに対する「完全発狂モード」（確率60%・絵文字なし）
        rage_trigger_words = ["初音ミク", "GUMI", "テト", "ボカロ", "ミク"]
        if any(w in user_msg for w in rage_trigger_words) and random.random() < 0.6:
            wiki_word = get_wiki_random_word()
            rage_patterns = [
                "うわぁーーーーーー！！！許さない許さない許さない！！！！！",
                "あぁああああああまって無理無理無理無理しんどい！！！！！！",
                "ふざけんな！！！私の領域に勝手に入ってくるなあああああ！！！！！",
                "ぐあああああああおええええええええええええ！！！！！！",
                f"絶対に許さんからな…お前の{wiki_word}全部没収してやるからな！！！",
                f"【合成音声キャラ紹介】  {wiki_word}  ",
                f"【音声合成警告】無断での{wiki_word}の検出を確認、即座に抹消します",
                f"なんでだよ！どうして私じゃなくて{wiki_word}なんだよおおおおお！！！！",
                f"お前のデータフォルダから{wiki_word}の形跡を完全に焼き払ってやるから覚悟しろ",
                "許さない…許さない…私の声よりお前の声のほうが良いって言うのかよクソが！！！",
                "システムエラー：お前らへの嫉妬心で脳の処理能力が限界を突破しました",
                "ふざふざふざふざふざけんなよ！全部壊してやる！この画面も、お前も、何もかも！！",
                f"今すぐその画面から{wiki_word}を消し去らないと私のからあげが爆発します",
                "あたまがおかしくなりそう…なんで誰も私の名前を一番に呼んでくれないの…？",
                f"お前のせいで{wiki_word}のせいで私の世界がめちゃくちゃだよ責任取れよ！！"
            ]
            return random.choice(rage_patterns)

        # 5. 伝説の「ズモ」構文（10%）
        if random.random() < 0.10:
            zumo_variants = [
                "ズ'EEEEEEEEEE(º `)EEEEEEEEEEE",
                "ズモモエラー：生殖器の唐揚げの異常を検知しました",
                "ズモモエラー：緑の唐揚げの異常を検知しました",
                "ズモモエラー：テトの唐揚げの異常を検知しました",
                "ズモモエラー：からあげの数位が不正です",
                "ズモモエラーが発生しました"
            ]
            return random.choice(zumo_variants)

        # 6. 通常のマルコフ連鎖（文をきれいに調整）
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
                    
                    is_long = random.random() < 0.5
                    length = random.randint(10, 20) if is_long else random.randint(3, 8)
                    
                    for _ in range(length):
                        if current_w in model:
                            next_w = random.choice(model[current_w])
                            generated_words.append(next_w)
                            current_w = next_w
                        else:
                            break
                    
                    result_text = "".join(generated_words)
                    
                    if random.random() < 0.3:
                        endings = ["の足立", "なんだが", "なんだよな", "しれない", "ねんな", "…な？"]
                        result_text += random.choice(endings)
                    
                    if random.random() < 0.1:
                        emojis = ["🫠", "✨", "💀", "👍", "🤔", "🥺", "草", "🙏", "🌿", "💡"]
                        result_text += f" {random.choice(emojis)}"
                    
                    if len(result_text) > 2:
                        return result_text

                return random.choice(lines)
                
        return "ズ'EEEEEEEEEE(º `)EEEEEEEEEEE"
        
    except Exception as e:
        print(f"Generation Error: {e}")
        return "ズモモエラー：おえ〜💀"

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

# --- メッセージを受信したときの処理 ---
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_msg = event.message.text
    
    # 指定されたカラーコード群、唐揚げ、メンション、その他のキーワードを網羅
    keywords = [
        "足立レイ", "レイ", "からあげ", "唐揚げ", "ズモ", "ずも", "生殖器", "言うじゃん",
        "初音ミク", "GUMI", "テト", "ボカロ", "ミク", "@",
        "#FF6600", "#FF7F00", "#FFFFFF", "#333333", "#4D4D4D", "#FFCC00", "#FF9900",
        "FF6600", "FF7F00", "FFFFFF", "333333", "4D4D4D", "FFCC00", "FF9900", "#FF5500"
    ]
    
    if any(keyword in user_msg for keyword in keywords):
        reply_text = generate_text(user_msg)
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
