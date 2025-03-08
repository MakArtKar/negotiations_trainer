import os

from fastapi import FastAPI
from dotenv import load_dotenv
from pydantic import BaseModel

from multiagents_simulator.coalition_negotiations_manager import (
    CoalitionNegotiationsManager,
    NegotiationStep,
)
from multiagents_simulator.one_on_one_negotiations_manager import (
    OneOnOneNegotiationsManager,
)

from multiagents_simulator.prompts.base import offer_creation_prompt

load_dotenv()

CASES_PATH = "multiagents_simulator/cases/"

app = FastAPI()

simulation_managers: dict[
    str, CoalitionNegotiationsManager | OneOnOneNegotiationsManager
] = {}


class Data(BaseModel):
    id: str
    message: str | None = None


@app.post("/create_simulation")
async def create_simulation(data: Data) -> list[str] | None:
    if data.id in simulation_managers:
        return None

    case = data.message.split(maxsplit=1)[1]
    manager_class = (
        CoalitionNegotiationsManager if case == "abc" else OneOnOneNegotiationsManager
    )
    simulation_managers[data.id] = manager_class(
        os.path.join(CASES_PATH, f"{case}.json"),
    )
    messages_to_send = [f"Rules:\n{simulation_managers[data.id].rules_prompt}\n"]
    if getattr(simulation_managers[data.id], "participants", None) is not None:
        messages_to_send.append(
            "Participants:\n"
            + ", ".join(simulation_managers[data.id].participants.keys())
            + "\n"
        )
    messages_to_send.append(offer_creation_prompt)
    return messages_to_send


@app.post("/end_simulation")
async def end_simulation(data: Data):
    if data.id in simulation_managers:
        del simulation_managers[data.id]


@app.post("/get_text")
async def get_text(data: Data) -> list[str] | None:
    manager = simulation_managers[data.id]
    if isinstance(manager, CoalitionNegotiationsManager):
        if manager.step == NegotiationStep.MAKE_OFFER:
            offers = manager.get_user_offer(data.message)
            messages_to_send = [
                f"Offer from participant {offer['from']}\n\n"
                + "\n".join(
                    [
                        f"{item['participant']}: {item['result']}"
                        for item in offer["offer"]
                    ]
                )
                + "\nParticipants: "
                + ", ".join(offer["participants"])
                for offer in offers
            ]
            messages_to_send.append(
                manager.make_offer_choosing_request(manager.human_participant)
            )
            return messages_to_send
        elif manager.step == NegotiationStep.CHOOSE_OFFER:
            accepted, accepted_offer = manager.choose_offer(data.message)
            if accepted_offer is None:
                if manager.step != NegotiationStep.NEGOTIATIONS_END:
                    messages_to_send = [
                        "No offer was chosen. The negotiations continue.",
                        "\n".join(
                            [
                                f"Offer from {participant} was accepted by "
                                + ", ".join(accepted_by)
                                for participant, accepted_by in accepted.items()
                            ]
                        ),
                        offer_creation_prompt,
                    ]
                    return messages_to_send
                else:
                    return None
            messages_to_send = [
                f"Participants accepted offer from {participant_name}: "
                + (
                    ", ".join(accepted[participant_name])
                    if len(accepted[participant_name]) > 0
                    else "nobody"
                )
                for participant_name in manager.participants
            ]
            messages_to_send.append(
                f"Accepted offer from participant {accepted_offer['from']}\n\n"
                + "\n".join(
                    [
                        f"{item['participant']}: {item['result']}"
                        for item in accepted_offer["offer"]
                    ]
                )
                + "\nParticipants: "
                + ", ".join(accepted_offer["participants"])
            )
            messages_to_send.append(
                "Negotiations are over - please, send /end_simulation"
            )
            return messages_to_send
        elif manager.step == NegotiationStep.NEGOTIATIONS_END:
            return None
    elif isinstance(manager, OneOnOneNegotiationsManager):
        result = manager.process_new_message(data.message)
        if result == "Accepted":
            return ["Your offer was accepted!"]
        elif manager.iteration == manager.max_iterations:
            return [
                "The negotiations are over - number of iterations are exceeded. Please, send /end_simulation."
            ]
        else:
            return [f"Your offer wasn't accepted, the reason:\n{result}"]
