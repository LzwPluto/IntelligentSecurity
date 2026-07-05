from ..services.device import DeviceController
from ..services.time_service import TimeService
from ..services.unknown import UnknownService
from ..services.sensor import SensorService


class Dispatcher:

    def __init__(self, music_service=None, feishu_service=None):

        self.handlers = {

            "device_control": DeviceController(),

            "music_play": music_service,

            "time_query": TimeService(),

            "sensor_query": SensorService(),

            "unknown": UnknownService(),

            "feishu": feishu_service,

        }

    def dispatch(self, tasks):

        """
        Dispatch all tasks returned by LLM.

        Parameters
        ----------
        tasks : list
            result["tasks"]
        """

        print("\n========== Dispatcher ==========\n")

        if not tasks:

            print("No task to execute.")

            return

        for task in tasks:

            intent = task.get("intent")

            params = task.get("params", {})

            print(f"[Dispatcher] {intent}")

            handler = self.handlers.get(intent)

            if handler is None:

                print(f"Unknown intent: {intent}")

                continue

            try:

                handler.execute(params)

            except Exception as e:

                print(f"{intent} execute failed.")

                print(e)

        print("\n======= Dispatcher End =======\n")
