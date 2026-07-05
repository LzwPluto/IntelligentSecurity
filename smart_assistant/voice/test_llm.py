from llm.api_client import DeepSeekClient

API_KEY = "sk-145acec119e44dc2847f446ee8d36f8f"


def main():

    llm = DeepSeekClient(API_KEY)

    result = llm.chat("打开客厅灯")

    print(result)


if __name__ == "__main__":
    main()
