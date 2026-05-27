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
                    "text": "📞 Called",
                    "callback_data": make_callback("called_broker", reference_id),
                },
                {
                    "text": "💸 Rate too low",
                    "callback_data": make_callback("rate_too_low", reference_id),
                },
            ],
            [
                {
                    "text": "🚚 Sent to driver",
                    "callback_data": make_callback("sent_to_driver", reference_id),
                },
                {
                    "text": "🙅 Driver rejected",
                    "callback_data": make_callback("driver_rejected", reference_id),
                },
            ],
            [
                {
                    "text": "⛔ Bad broker",
                    "callback_data": make_callback("bad_broker", reference_id),
                },
                {
                    "text": "❌ Covered",
                    "callback_data": make_callback("covered", reference_id),
                },
            ],
            [
                {
                    "text": "⏭️ Skip",
                    "callback_data": make_callback("skipped", reference_id),
                },
                {
                    "text": "📝 Other",
                    "callback_data": make_callback("other", reference_id),
                },
            ],
        ]

    else:
        buttons = [
            [
                {
                    "text": "✅ Booked",
                    "callback_data": make_callback("booked", reference_id),
                },
                {
                    "text": "📞 Called",
                    "callback_data": make_callback("called_broker", reference_id),
                },
            ],
            [
                {
                    "text": "🚚 Sent to driver",
                    "callback_data": make_callback("sent_to_driver", reference_id),
                },
                {
                    "text": "💸 Rate too low",
                    "callback_data": make_callback("rate_too_low", reference_id),
                },
            ],
            [
                {
                    "text": "⛔ Bad broker",
                    "callback_data": make_callback("bad_broker", reference_id),
                },
                {
                    "text": "❌ Covered",
                    "callback_data": make_callback("covered", reference_id),
                },
            ],
        ]

    return {
        "inline_keyboard": buttons,
    }