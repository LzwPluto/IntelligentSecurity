import json
import re


class LLMParser:
    """
    DeepSeek 返回结果解析器

    功能：
    1. 去除 Markdown 包裹
    2. JSON 解析
    3. 校验返回格式
    4. 返回 Python dict
    """

    def parse(self, response: str) -> dict:
        """
        Parameters
        ----------
        response : str
            LLM 返回的字符串

        Returns
        -------
        dict
            Python 字典
        """

        if response is None:
            raise ValueError("LLM response is None.")

        response = response.strip()

        # 去掉 Markdown ```json
        response = re.sub(r"^```json", "", response)
        response = re.sub(r"^```", "", response)
        response = re.sub(r"```$", "", response)

        response = response.strip()

        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"JSON Parse Error:\n{e}\n\nOriginal Response:\n{response}"
            )

        self._check_format(data)

        return data

    def _check_format(self, data: dict):
        """
        检查 JSON 是否符合协议
        """

        # ---------- 顶层字段 ----------
        required_keys = [
            "success",
            "tasks",
            "reply",
        ]

        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing field: {key}")

        # ---------- success ----------
        if not isinstance(data["success"], bool):
            raise ValueError("success must be bool.")

        # ---------- reply ----------
        if not isinstance(data["reply"], str):
            raise ValueError("reply must be str.")

        # ---------- tasks ----------
        if not isinstance(data["tasks"], list):
            raise ValueError("tasks must be list.")

        # ---------- 每一个 task ----------
        for i, task in enumerate(data["tasks"]):

            if not isinstance(task, dict):
                raise ValueError(f"Task {i} must be dict.")

            if "intent" not in task:
                raise ValueError(f"Task {i} missing intent.")

            if "params" not in task:
                raise ValueError(f"Task {i} missing params.")

            if not isinstance(task["intent"], str):
                raise ValueError(f"Task {i} intent must be str.")

            if not isinstance(task["params"], dict):
                raise ValueError(f"Task {i} params must be dict.")
