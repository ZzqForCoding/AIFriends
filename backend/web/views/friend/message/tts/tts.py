import base64
import os

from rest_framework.views import APIView
from rest_framework.response import Response
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer

class TtsView(APIView):
    def post(self, request):
        text = request.data['text']
        if not text:
            return Response({'result': '文本不能为空'})
        try:
            audio_base64 = self.synthesize_text(text)
            return Response({
                'result': 'success',
                'audio': audio_base64
            })
        except Exception as e:
            return Response({'result': f'语音合成失败: {str(e)}'})
    
    def synthesize_text(self, text):
        """
        非流式语音合成，返回 base64 编码的 mp3 音频
        """
        # 复用你现有的环境变量，如果没有就设一个 DASHSCOPE_API_KEY
        dashscope.api_key = os.getenv('API_KEY')

        synthesizer = SpeechSynthesizer(
            model="cosyvoice-v3-flash",
            voice="longanyang",
            volume=50,
            speech_rate=1.25,
            pitch_rate=1
        )
        
        # call() 是阻塞的，一次性返回完整音频（bytes）
        audio = synthesizer.call(text)
        if not audio:
            raise RuntimeError('语音合成失败，未返回音频数据')
        
        return base64.b64encode(audio).decode('utf-8')
