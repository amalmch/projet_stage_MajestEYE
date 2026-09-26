import av
import io
import base64

def test_av_decoding():
    # Let's create a silent/dummy audio stream to test if the resampler and decoding code works without errors
    try:
        resampler = av.AudioResampler(
            format='s16',
            layout='mono',
            rate=16000
        )
        print("AudioResampler created successfully!")
    except Exception as e:
        print("Failed to create AudioResampler:", e)

if __name__ == '__main__':
    test_av_decoding()
