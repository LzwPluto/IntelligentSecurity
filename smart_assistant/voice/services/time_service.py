from datetime import datetime
from .base import BaseService


class TimeService(BaseService):

    def execute(self, params):

        print("\n========== Time ==========")
        print(datetime.now())
        print("==========================\n")
