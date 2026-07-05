from .base import BaseService


class UnknownService(BaseService):

    def execute(self, params):

        print("\n========== Unknown ==========")
        print("Can not understand command.")
        print("=============================\n")
