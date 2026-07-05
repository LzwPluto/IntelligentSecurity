from llm.parser import LLMParser

response = """
{
    "success": true,
    "tasks": [
        {
            "intent": "device_control",
            "params": {
                "device": "light",
                "location": "living_room",
                "action": "on"
            }
        },
        {
            "intent": "weather_query",
            "params": {
                "city": "北京"
            }
        }
    ],
    "reply": "好的，已打开客厅灯，现在查询北京天气。"
}
"""

parser = LLMParser()

result = parser.parse(response)

print(result)

print()

print("success:", result["success"])

print()

print("reply:", result["reply"])

print()

for task in result["tasks"]:
    print(task)
