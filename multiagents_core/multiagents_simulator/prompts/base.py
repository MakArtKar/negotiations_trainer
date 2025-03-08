offer_creation_prompt = "Please, propose the offer to other participants."

offer_acceptance_prompt = "Please, choose one or zero of proposed offers - send only the name of its author. If no offers suits for you - return the reason why.\n{offers}"

info_extraction_prompt = (
    "You should extract the information about offer from text: participants of this offer and for each participant extract the part that is connected to him (what he gets).\n"
    "All players: {participants}.\nIf some player is not a participant of this offer - give him 0."
)

participant_prompt = (
    "Your name is {name} and you are a participant of negotiations.\n"
    "Here are the rules of these negotiations:\n\n{rules_prompt}\n\n"
    "1) You can make offers to other participants in arbitrary text format\n"
    "2) You can accept proposed offers from other participants - you can accept one of the offers or refuse all of them.\n"
    "If you accept some of the offers - return participant's name whose offer you accept. Otherwise, return the reason, why you didn't refuse the offer.\n"
)
