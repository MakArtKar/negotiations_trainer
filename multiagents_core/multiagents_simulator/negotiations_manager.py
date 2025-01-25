import json
from collections import defaultdict
from enum import Enum
from typing import Any, Callable

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


from .prompts.base import (
    offer_acceptance_prompt,
    offer_creation_prompt,
    info_extraction_prompt,
    participant_prompt,
)


class NegotiationStep(Enum):
    MAKE_OFFER = 0
    CHOOSE_OFFER = 1
    NEGOTIATIONS_END = 2


class NegotiationsManager:
    def __init__(
        self,
        case: str,
        max_iterations: int = 5,
        info_extration_agent_kwargs: dict[str, dict[str, Any]] | None = None,
        agent_kwargs: dict[str, dict[str, Any]] | None = None,
    ):
        with open(case, "r") as f:
            case = json.load(f)
        self.max_iterations = max_iterations
        self.rules_prompt = case["rules"]
        self.participants = case["participants"]
        self.human_participant = [
            name for name in self.participants if self.participants[name] == "human"
        ][0]
        self.info_extration_agent_kwargs = info_extration_agent_kwargs
        self.agent_kwargs = agent_kwargs

        self.offers = None
        self.participant_offers = None
        self.accepted_offer = None
        self.init()

        self.current_iteration = 0
        self.step = NegotiationStep.MAKE_OFFER

    def init(self):
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Offer extraction helper",
            content=info_extraction_prompt,
        )
        if (
            self.info_extration_agent_kwargs is not None
            and "model" not in self.info_extration_agent_kwargs
        ):
            self.info_extration_agent_kwargs["model"] = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O,
            )
        self.info_extration_agent = ChatAgent(
            system_message=sys_msg,
            **(
                self.info_extration_agent_kwargs
                if self.info_extration_agent_kwargs is not None
                else {}
            ),
        )

        self.agents: dict[str, ChatAgent] = {}
        for participant_name, participant_type in self.participants.items():
            if participant_type == "agent":
                sys_msg = BaseMessage.make_assistant_message(
                    role_name=f"Negotiations participant {participant_name}",
                    content=participant_prompt.format(
                        name=participant_name, rules_prompt=self.rules_prompt
                    ),
                )

                agent_kwargs = (
                    self.agent_kwargs.get(participant_name, {})
                    if self.agent_kwargs
                    else {}
                )
                if "model" not in agent_kwargs:
                    agent_kwargs["model"] = ModelFactory.create(
                        model_platform=ModelPlatformType.OPENAI,
                        model_type=ModelType.GPT_4O,
                    )

                self.agents[participant_name] = ChatAgent(
                    system_message=sys_msg,
                    **agent_kwargs,
                )

    def get_user_offer(self, offer: str) -> list[dict[str, Any]]:
        self.offers = []
        self.participant_offers = defaultdict(list)
        for participant_name, participant_type in self.participants.items():
            if participant_type == "human":
                result = offer
            else:
                result = (
                    self.agents[participant_name]
                    .step(offer_creation_prompt)
                    .msgs[-1]
                    .content
                )

            participants = (
                self.info_extration_agent.step(result).msgs[-1].content.split(";")
            )
            participants = [participant.strip() for participant in participants]
            participants = list(set(participants) - set(participant_name))
            self.offers.append(
                {
                    "from": participant_name,
                    "participants": participants,
                    "offer": result,
                }
            )
            for to in participants:
                self.participant_offers[to].append(self.offers[-1])

        self.step = NegotiationStep.CHOOSE_OFFER
        return self.offers

    def make_offer_choosing_request(self, participant_name: str) -> str:
        offers_list = self.participant_offers[participant_name]
        if len(offers_list) == 0:
            return None
        str_offers_list = [
            f"Offer author: {offer['from']}\nParticipants: {offer['participants']}\nOffer: {offer['offer']}"
            for offer in offers_list
        ]
        return offer_acceptance_prompt.format(offers="\n\n".join(str_offers_list))

    def choose_offer(self, human_chosen_offer: str | None) -> dict[str, Any] | None:
        accepted = {key: [] for key in self.participants.keys()}
        for participant_name in self.participant_offers:
            if self.participants[participant_name] == "agent":
                prompt = self.make_offer_choosing_request(participant_name)
                result = self.agents[participant_name].step(prompt).msgs[-1].content
            else:
                result = human_chosen_offer

            if result in accepted:
                accepted[result].append(participant_name)

        self.accepted_offer = None
        for offer in self.offers:
            if len(offer["participants"]) == len(accepted[offer["from"]]):
                self.accepted_offer = offer
                break

        self.end_iteration()

        if self.accepted_offer is None:
            return accepted, None

        self.step = NegotiationStep.NEGOTIATIONS_END
        return accepted, self.accepted_offer

    def end_iteration(self):
        self.offers = None
        self.participant_offers = None
        self.current_iteration += 1
        if (
            self.current_iteration == self.max_iterations
            or self.accepted_offer is not None
        ):
            self.step = NegotiationStep.NEGOTIATIONS_END
        else:
            self.step = NegotiationStep.MAKE_OFFER


"""
Old code
"""


class OldNegotiationsManager:
    def __init__(
        self,
        case: str,
        max_iterations: int = 5,
        agent_kwargs: dict[str, dict[str, Any]] | None = None,
        info_extration_agent_kwargs: dict[str, dict[str, Any]] | None = None,
        send_message_to_human_func: Callable[[str], str | None] | None = None,
    ):
        with open("case", "r") as f:
            case = json.load(f)
        self.rules_prompt = case["rules"]
        self.participants = case["participants"]
        self.max_iterations = max_iterations
        self.agent_kwargs = agent_kwargs or {}
        self.info_extration_agent_kwargs = info_extration_agent_kwargs or {}
        if send_message_to_human_func is None and "human" in self.participants.values():
            raise ValueError(
                'If there is a "human" type agent in `participants` - `send_message_to_human_func` can\'t be None.'
            )
        self.send_message_to_human_func = send_message_to_human_func

        self.agents = None
        self.info_extration_agent = None
        self.init()
        self.send_message_to_human_func(self.rules_prompt)

    def init(self):
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Offer extraction helper",
            content=info_extraction_prompt,
        )
        if "model" not in self.info_extration_agent_kwargs:
            self.info_extration_agent_kwargs["model"] = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O,
            )
        self.info_extration_agent = ChatAgent(
            system_message=sys_msg,
            **self.info_extration_agent_kwargs,
        )

        self.agents = {}
        for participant_name, participant_type in self.participants.items():
            if participant_type == "agent":
                sys_msg = BaseMessage.make_assistant_message(
                    role_name=f"Negotiations participant {participant_name}",
                    content=participant_prompt.format(
                        name=participant_name, rules_prompt=self.rules_prompt
                    ),
                )

                agent_kwargs = self.agent_kwargs.get(participant_name, {})
                if "model" not in agent_kwargs:
                    agent_kwargs["model"] = ModelFactory.create(
                        model_platform=ModelPlatformType.OPENAI,
                        model_type=ModelType.GPT_4O,
                    )

                self.agents[participant_name] = ChatAgent(
                    system_message=sys_msg,
                    **agent_kwargs,
                )

    def run_negotiations(self) -> dict[str, Any] | None:
        for iteration in range(self.max_iterations):
            self.send_message_to_human_func(f"Starting iteration {iteration}")
            offer = self.run_negotiations_round()
            if offer is not None:
                return offer
        return None

    def run_negotiations_round(self) -> dict[str, Any] | None:
        offers = []
        participant_offers = defaultdict(list)
        for participant_name, participant_type in self.participants.items():
            if participant_type == "agent":
                result = (
                    self.agents[participant_name]
                    .step(offer_creation_prompt)
                    .msgs[-1]
                    .content
                )
            else:
                result = self.send_message_to_human_func(offer_creation_prompt)

            participants = (
                self.info_extration_agent.step(result).msgs[-1].content.split(";")
            )
            participants = [participant.strip() for participant in participants]
            participants = list(set(participants) - set(participant_name))
            offers.append(
                {
                    "from": participant_name,
                    "participants": participants,
                    "offer": result,
                }
            )
            if participant_type == "agent":
                self.send_message_to_human_func(
                    f"Offer from agent {participant_name}\n\n{result}\nParticipants: ",
                    ", ".join(participants),
                )

            for to in participants:
                participant_offers[to].append(offers[-1])

        n_accepted = defaultdict(int)
        for participant_name, offers_list in participant_offers.items():
            if len(offers_list) == 0:
                continue
            str_offers_list = [
                f"Offer author: {offer['from']}\nParticipants: {offer['participants']}\nOffer: {offer['offer']}"
                for offer in offers_list
            ]
            prompt = offer_acceptance_prompt.format(offers="\n\n".join(str_offers_list))

            if self.participants[participant_name] == "agent":
                result = self.agents[participant_name].step(prompt).msgs[-1].content
                self.send_message_to_human_func(
                    f"Participant {participant_name} accepted offer from participant {result}"
                )
            else:
                result = self.send_message_to_human_func(prompt)

            n_accepted[result] += 1

        accepted_offer = None
        for offer in offers:
            if len(offer["participants"]) == n_accepted[offer["from"]]:
                accepted_offer = offer
                break

        if accepted_offer is None:
            return None

        return accepted_offer
