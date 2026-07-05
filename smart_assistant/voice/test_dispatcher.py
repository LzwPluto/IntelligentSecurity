from dispatcher.dispatcher import Dispatcher


result = {
    "success": True,
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
        },
        {
            "intent": "music_play",
            "params": {
                "artist": "周杰伦"
            }
        },
        {
            "intent": "time_query",
            "params": {}
        }
    ],
    "reply": "好的，正在执行。"
}

dispatcher = Dispatcher()

dispatcher.dispatch(result)
