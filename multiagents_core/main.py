import os

from fastapi import FastAPI
from dotenv import load_dotenv
from pydantic import BaseModel

from multiagents_simulator.negotiations_manager import (
    NegotiationsManager,
    NegotiationStep,
)
from multiagents_simulator.prompts.base import offer_creation_prompt

load_dotenv()

CASES_PATH = "multiagents_simulator/cases/"

app = FastAPI()

simulation_managers: dict[str, NegotiationsManager] = {}


class Data(BaseModel):
    id: str
    message: str | None = None


@app.post("/create_simulation")
async def create_simulation(data: Data) -> list[str] | None:
    if data.id in simulation_managers:
        return None
    simulation_managers[data.id] = NegotiationsManager(
        os.path.join(CASES_PATH, "abc.json"),
    )
    return [
        f"Rules:\n{simulation_managers[data.id].rules_prompt}\n",
        "Participants:\n"
        + ", ".join(simulation_managers[data.id].participants.keys())
        + "\n",
        offer_creation_prompt,
    ]


@app.post("/end_simulation")
async def end_simulation(data: Data):
    if data.id in simulation_managers:
        del simulation_managers[data.id]


@app.post("/get_text")
async def get_text(data: Data) -> list[str] | None:
    manager = simulation_managers[data.id]
    if manager.step == NegotiationStep.MAKE_OFFER:
        offers = manager.get_user_offer(data.message)
        messages_to_send = [
            f"Offer from participant {offer['from']}\n\n{offer['offer']}\nParticipants: "
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
            f"Accepted offer from participant {accepted_offer['from']}\n\n{accepted_offer['offer']}\nParticipants: "
            + ", ".join(accepted_offer["participants"])
        )
        messages_to_send.append("Negotiations are over - please, send /end_simulation")
        return messages_to_send
    elif manager.step == NegotiationStep.NEGOTIATIONS_END:
        return None
