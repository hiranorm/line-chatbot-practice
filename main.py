import os
import errno
import tempfile
from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage,ImageMessage, TextSendMessage, FollowEvent
)

# 画像認識のためのインポート
from keras.models import Sequential, load_model
from keras.preprocessing import image
import tensorflow as tf
import numpy as np

# 普通の機能用
app = Flask(__name__)

line_bot_api = LineBotApi('85GuDL0mm/fktE/4QksofPV5VrmZQVbS2/VhT+F1wiu356SJk/lLyXUN+F4vqEr8Dd60RnjR32/7sQ0vcPvOrXUMUpoegYOXR6S04McNNJ1cn1CwwZyc7aHkC396KD+iszTsSPN5yKUXu752goSzGwdB04t89/1O/w1cDnyilFU=') #アクセストークンを入れてください
handler = WebhookHandler('d9040f4fffb01b6c55812dc39bbdcd69') #Channel Secretを入れてください

# 画像認識のためのコード
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
try:
    os.makedirs(static_tmp_path)
except OSError as exc:
    if exc.errno == errno.EEXIST and os.path.isdir(static_tmp_path):
        pass
    else:
        raise

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# テキストメッセージが送信されたときの処理
@handler.add(MessageEvent, message=TextMessage) #引数に処理したいイベントを指定してください
def handle_message(event):
    text = event.message.text
    if text == 'おはよう':
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='おはようございます!'))
    elif text == 'こんにちは':
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='こんにちは！'))
    elif text == '画像認識して':
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='だが断る！'))
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=event.message.text))

# 以下、送信された画像を保存するためのコード
class_label = ["飛行機","自動車","鳥","猫","鹿","犬","蛙","馬","船","トラック"]
graph = tf.get_default_graph() # kerasのバグでこのコードが必要.
model = load_model('my_model.h5') # 学習済みモデルをロードする

@handler.add(MessageEvent, message=ImageMessage)
def handle_content_message(event):
    global graph
    with graph.as_default():
        message_content = line_bot_api.get_message_content(event.message.id)
        with tempfile.NamedTemporaryFile(dir=static_tmp_path, prefix="jpg" + '-', delete=False) as tf:
            for chunk in message_content.iter_content():
                tf.write(chunk)
                tempfile_path = tf.name

        dist_path = tempfile_path + '.' + "jpg"
        dist_name = os.path.basename(dist_path)
        os.rename(tempfile_path, dist_path)

        filepath = os.path.join('static', 'tmp', dist_name) # 送信された画像のパスが格納されている

# 以下、送信された画像をモデルに入れる
        img = image.load_img(filepath, target_size=(32, 32)) # 送信された画像を読み込み、リサイズする
        img = image.img_to_array(img) # 画像データをndarrayに変換する
        data = np.array([img]) # model.predict()で扱えるデータの次元にそろえる

        result = model.predict(data)
        predicted = result.argmax() # 予測結果が格納されている
        pred_answer = "これは" + class_label[predicted] + "です。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=pred_answer))


# フォローイベント時の処理
@handler.add(FollowEvent)
def handle_follow(event):
    # 誰が追加したかわかるように機能追加
    profile = line_bot_api.get_profile(event.source.user_id)  # 取得したプロフィールをprofileに格納しています
    line_bot_api.push_message('Uad6b2718be2fa3e98ecdd9e783aa83c8',
                              TextSendMessage(text="表示名:{}\ユーザID:{}\n画像のURL:{}\nステータスメッセージ:{}" \
                                              .format(profile.display_name, profile.user_id, profile.picture_url,
                                                      profile.status_message)))

    # 友達追加したユーザにメッセージを送信
    line_bot_api.reply_message(
        event.reply_token, TextSendMessage(text='友達追加ありがとうございます'))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host ='0.0.0.0',port = port)