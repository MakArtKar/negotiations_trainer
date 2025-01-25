import json
import os
from typing import Any

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

from .prompts.base import (
    offer_acceptance_prompt,
    participant_prompt,
)


class OneOnOneNegotiationsManager:
    def __init__(
        self,
        case_path: str,
        max_iterations: int = 5,
        agent_kwargs: dict[str, dict[str, Any]] | None = None,
    ):
        with open(case_path, "r") as f:
            case = json.load(f)
        self.max_iterations = max_iterations
        self.rules_prompt = case["rules"]
        self.agent_name = case["agent_name"]
        self.human_name = case["human_name"]
        if "agent_context" in case:
            with open(
                os.path.join(os.path.dirname(case_path), case["agent_context"]), "r"
            ) as f:
                self.agent_context = f.read()
        self.agent_kwargs = agent_kwargs or {}

        self.iteration = 0
        self.agent = None
        self.init()

    def init(self):
        sys_msg = BaseMessage.make_assistant_message(
            role_name=f"Negotiations participant {self.agent_name}",
            content=participant_prompt.format(
                name=self.agent_name, rules_prompt=self.rules_prompt
            )
            + f"\n\nHere is extra information about the case and how you should behave.\n{self.agent_context}",
        )

        if "model" not in self.agent_kwargs:
            self.agent_kwargs["model"] = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O,
            )

        self.agent = ChatAgent(
            system_message=sys_msg,
            **self.agent_kwargs,
        )

    def process_new_message(self, message: str) -> str:
        result = (
            self.agent.step(
                offer_acceptance_prompt.format(
                    offers=f"Author: {self.human_name}\nOffer: {message}"
                )
            )
            .msgs[-1]
            .content
        )
        if result == self.human_name:
            return "Accepted"
        self.iteration += 1
        return result
