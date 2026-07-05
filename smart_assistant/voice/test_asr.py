from asr.recognizer import SenseVoiceRecognizer


def main():

    asr = SenseVoiceRecognizer()

    result = asr.recognize("asr/output.wav")

    print("\n============================")
    print("SenseVoice Result:")
    print("============================")
    print(result)
    print("============================")


if __name__ == "__main__":
    main()
