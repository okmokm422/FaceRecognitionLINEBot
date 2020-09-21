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
    MessageEvent, TextMessage, TextSendMessage, ImageMessage  # 追記
)

# バイナリデータとして画像を扱う
from io import BytesIO

# AzureのPython SDKライブラリ
from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials

app = Flask(__name__)

# 環境変数からトークンを読み込み
# LINE
YOUR_CHANNEL_ACCESS_TOKEN = os.getenv('YOUR_CHANNEL_ACCESS_TOKEN')
YOUR_CHANNEL_SECRET = os.getenv('YOUR_CHANNEL_SECRET')
line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

# LINE
YOUR_FACE_API_KEY = os.environ["YOUR_FACE_API_KEY"]
YOUR_FACE_API_ENDPOINT = os.environ["YOUR_FACE_API_ENDPOINT"]
face_client = FaceClient(
    YOUR_FACE_API_ENDPOINT,
    CognitiveServicesCredentials(YOUR_FACE_API_KEY)
)

# PERSON GROUP
PERSON_GROUP_ID = os.getenv('PERSON_GROUP_ID')
PERSON_ID_AUDREY = os.getenv('PERSON_ID_AUDREY')

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
    try:
        # メッセージIDを受け取る
        message_id = event.message.id
        # メッセージIdに含まれるmassage_contentを抽出する
        message_content = line_bot_api.get_message_content(message_id)
        # contentの画像データをバイナリデータとして扱えるようにする
        image = BytesIO(message_content.content)
        # Detect from streamで顔検出
        detected_faces = face_client.face.detect_with_stream(image)
        print(detected_faces)

        # 検出結果に応じて処理を分ける
        if detected_faces != []:
            # 顔検出ができたら顔認証を行う
            valifired = face_client.face.verify_face_to_person(
                face_id=detected_faces[0].face_id,
                person_group_id=PERSON_GROUP_ID,
                person_id=PERSON_ID_AUDREY
            )
            # 認証結果に応じて処理を変える
            if valifired:
                if varifired.is_identical:
                    # 顔認証が一致した場合
                    text = 'この写真はオードリーヘップバーンです(score:{:.3f}).format(varified.confidence)'
                else:
                    # 顔認証が一致しなかった場合
                    text = 'この写真はオードリーヘップバーンではありません(score:{:.3f}).format(varified.confidence)'
            else:
                text = '識別できませんでした。'
        else:
            # 顔検出されない場合のメッセージ
            text = '写真から顔が検出できませんでした。他の画像で試してください。'
    except:
        # エラー時のメッセージ
        text = 'error'

        # LINEチャネルを通じてメッセージを応答
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=text)
        )


# app.pyがメインスコープとして呼ばれた際には、appを起動
if __name__ == "__main__":
    app.run()
