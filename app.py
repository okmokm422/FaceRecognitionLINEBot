# coding: utf-8

# 機密情報に関しては環境変数で管理
import os 

from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)

# textとimageを扱えるようにする
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageMessage # 追記
)

app = Flask(__name__)

# 環境変数からトークンを読み込み
YOUR_CHANNEL_ACCESS_TOKEN = os.getenv('YOUR_CHANNEL_ACCESS_TOKEN')
YOUR_CHANNEL_SECRET = os.getenv('YOUR_CHANNEL_SECRET')

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)


# 後述のwebhook通信をLINEチャネルから受け取るためのエンドポイントを設定
@app.route("/callback", methods=['POST'])
def callback():
    # リクエスト元が正当なものであるのかを判断するためのヘッダー情報を抽出
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # リクエストのbodyを抽出
    # bodyにはチャネルに送信されてきたテキストメッセージ等が含まれている
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # チャンネルに送信されてきたイベントに応じてBOTの挙動を定義
    # Signatureが正当なものであるか判定
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# 「イベントがメッセージイベントであり」、かつ、「テキストメッセージ」である場合の挙動
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # reply先（reply_token）と送信する内容(massage.text)を設定
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text))

# 画像メッセージのときの挙動
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    # LINEチャネルを通じてメッセージを応答
    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text='画像です')
    )

# app.pyがメインスコープとして呼ばれた際には、appを起動
if __name__ == "__main__":
    app.run()