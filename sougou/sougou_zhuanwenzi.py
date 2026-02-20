def textToAudio_Sougou(message, filePath):
    # https://ai.so    gou.com/doc/?url=/docs/content/tts/references/rest/
    '''
    curl -X POST \
         -H "Content-Type: application/json" \
         --data '{
      "appid": "xxx",
      "appkey": "xxx",
      "exp": "3600s"
    }' https://api.zhiyin.sogou.com/apis/auth/v1/create_token
    '''

    token = 'xxx'
    headers = {
        'Authorization': 'Bearer ' + token,
        'Appid': 'xxx',
        'Content-Type': 'application/json',
        'appkey': 'xxx',
        'secretkey': 'xxx'
    }
    data = {
        'input': {
            'text': message
        },
        'config': {
            'audio_config': {
                'audio_encoding': 'LINEAR16',
                'pitch': 1.0,
                'volume': 1.0,
                'speaking_rate': 1.0
            },
            'voice_config': {
                'language_code': 'zh-cmn-Hans-CN',
                'speaker': 'female'
            }
        }
    }

    result = requests.post(url=url, headers=headers, data=json.dumps(data, ensure_ascii=False).encode('utf-8')).content
    with open(filePath, 'wb') as f:
        f.write(result)