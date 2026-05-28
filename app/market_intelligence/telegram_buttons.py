def make_callback(feedback_type, reference_id=""):
    reference_id = str(reference_id or "").strip()

    if reference_id and reference_id.upper() != "NO ID":
        return f"fb|{feedback_type}|{reference_id}"

    return f"fb|{feedback_type}"


def build_feedback_buttons(message_kind="load", reference_id=""):
    if message_kind == "review_once":
        buttons = [
            [
                {
                    "text": "рџ“ћ Called",
                    "callback_data": make_callback("called_broker", reference_id),
                },
                {
                    "text": "рџ’ё Rate too low",
                    "callback_data": make_callback("rate_too_low", reference_id),
                },
            ],
            [
                {
                    "text": "рџљљ Sent to driver",
                    "callback_data": make_callback("sent_to_driver", reference_id),
                },
                {
                    "text": "рџ™… Driver rejected",
                    "callback_data": make_callback("driver_rejected", reference_id),
                },
            ],
            [
                {
                    "text": "в›” Bad broker",
                    "callback_data": make_callback("bad_broker", reference_id),
                },
                {
                    "text": "вќЊ Covered",
                    "callback_data": make_callback("covered", reference_id),
                },
            ],
            [
                {
                    "text": "вЏ­пёЏ Skip",
                    "callback_data": make_callback("skipped", reference_id),
                },
                {
                    "text": "рџ“ќ Other",
                    "callback_data": make_callback("other", reference_id),
                },
            ],
        ]

    else:
        buttons = [
            [
                {
                    "text": "вњ… Booked",
                    "callback_data": make_callback("booked", reference_id),
                },
                {
                    "text": "рџ“ћ Called",
                    "callback_data": make_callback("called_broker", reference_id),
                },
            ],
            [
                {
                    "text": "рџљљ Sent to driver",
                    "callback_data": make_callback("sent_to_driver", reference_id),
                },
                {
                    "text": "рџ’ё Rate too low",
                    "callback_data": make_callback("rate_too_low", reference_id),
                },
            ],
            [
                {
                    "text": "в›” Bad broker",
                    "callback_data": make_callback("bad_broker", reference_id),
                },
                {
                    "text": "вќЊ Covered",
                    "callback_data": make_callback("covered", reference_id),
                },
            ],
        ]

    return {
        "inline_keyboard": buttons,
    }
