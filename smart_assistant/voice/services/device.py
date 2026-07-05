from .base import BaseService
from . import led_control
from config import LED_GPIO_CHIP, LED_GPIO_PIN


class DeviceController(BaseService):

    def execute(self, params):

        print("\n========== Device Controller ==========")

        device = params.get("device")
        location = params.get("location")
        action = params.get("action")

        print(f"Device   : {device}")
        print(f"Location : {location}")
        print(f"Action   : {action}")

        if device == "light" or device == "led":
            led_control.init(LED_GPIO_PIN, LED_GPIO_CHIP)

            if action == "on":
                led_control.on()
            elif action == "off":
                led_control.off()
            elif action == "blink":
                led_control.blink()
            elif action == "toggle":
                led_control.blink()
            else:
                print(f"[Device] Unknown action: {action}")

        print("=======================================\n")
