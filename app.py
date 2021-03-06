# coding: utf-8

# 機密情報に関しては環境変数で管理
from flask.logging import create_logger
import os

from flask import Flask, request, abort
from flask.logging import create_logger  # app.loggerのエラー防止

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)

# textとimageを扱えるようにする
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageMessage
)

# バイナリデータとして画像を扱う
from io import BytesIO

# AzureのPython SDKライブラリ
from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials

app = Flask(__name__)
log = create_logger(app)

# 環境変数からトークンを読み込み
# LINE
YOUR_CHANNEL_ACCESS_TOKEN = os.getenv('YOUR_CHANNEL_ACCESS_TOKEN')
YOUR_CHANNEL_SECRET = os.getenv('YOUR_CHANNEL_SECRET')
line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

# FACE API
YOUR_FACE_API_KEY = os.environ["YOUR_FACE_API_KEY"]
YOUR_FACE_API_ENDPOINT = os.environ["YOUR_FACE_API_ENDPOINT"]
face_client = FaceClient(
    YOUR_FACE_API_ENDPOINT,
    CognitiveServicesCredentials(YOUR_FACE_API_KEY)
)

# PERSON GROUP
PERSON_GROUP_ID = os.getenv('PERSON_GROUP_ID')
PERSON_ID_HANZAWA = os.getenv('PERSON_ID_HANZAWA')
PERSON_ID_OWADA = os.getenv('PERSON_ID_OWADA')
PERSON_ID_KUROSAKI = os.getenv('PERSON_ID_KUROSAKI')


# 後述のwebhook通信をLINEチャネルから受け取るためのエンドポイントを設定

@app.route("/callback", methods=['POST'])
def callback():
    # リクエスト元が正当なものであるのかを判断するためのヘッダー情報を抽出
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # リクエストのbodyを抽出
    # bodyにはチャネルに送信されてきたテキストメッセージ等が含まれている
    body = request.get_data(as_text=True)
    log.info("Request body: " + body)

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
        # メッセージIDに含まれるmessage_contentを抽出する
        message_content = line_bot_api.get_message_content(message_id)
        # contentの画像データをバイナリデータとして扱えるようにする
        image = BytesIO(message_content.content)

        # Detect from streamで顔検出
        detected_faces = face_client.face.detect_with_stream(image)
        print(detected_faces)

        # 検出結果に応じて処理を分ける

        if detected_faces != []:

            # 検出された顔の最初のIDを取得
            text = detected_faces[0].face_id

            # 顔検出ができたら顔認証を行う
            valified_hanzawa = face_client.face.verify_face_to_person(
                face_id=detected_faces[0].face_id,
                person_group_id=PERSON_GROUP_ID,
                person_id=PERSON_ID_HANZAWA
            )
            valified_owada = face_client.face.verify_face_to_person(
                face_id=detected_faces[0].face_id,
                person_group_id=PERSON_GROUP_ID,
                person_id=PERSON_ID_OWADA
            )
            valified_kurosaki = face_client.face.verify_face_to_person(
                face_id=detected_faces[0].face_id,
                person_group_id=PERSON_GROUP_ID,
                person_id=PERSON_ID_KUROSAKI
            )

            score_hanzawa = valified_hanzawa.confidence
            score_owada = valified_owada.confidence
            score_kurosaki = valified_kurosaki.confidence

            # 認証結果に応じて処理を変える
            # スコアに応じて結果を返す
            if (valified_hanzawa or valified_owada or valified_kurosaki) \
                    and (score_hanzawa > 0.6 or score_owada > 0.6 or score_kurosaki > 0.6):

                if (score_hanzawa > score_owada) and (score_hanzawa > score_kurosaki):
                    text = 'この写真は半沢直樹です(半沢score : {})'.format(score_hanzawa)

                elif (score_owada > score_hanzawa) and (score_owada > score_kurosaki):
                    text = 'この写真は大和田取締役です(大和田score : {})'.format(score_owada)
                else:
                    text = 'この写真は黒崎検査官です(黒崎score : {})'.format(score_kurosaki)

            else:
                text = '半沢直樹、大和田取締役、黒崎検査官ではありません。'

        else:
            # 検出されない場合のメッセージ
            text = "no faces detected"
            text = "写真から顔が検出できませんでした。他の画像で試してください。"

    except:
        # エラー時のメッセージ
        text = "error"
    # LINEチャネルを通じてメッセージを返答
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=text)
    )


# app.pyがメインスコープとして呼ばれた際には、appを起動
if __name__ == "__main__":
    app.run()
