"""
Replies for the deterministic checks: replies that keep every rule, and for each check one reply
that deliberately breaks it. All text here is invented for the tests.
"""

PERSON_WORDS = (
    "I keep feeling stuck, like I am behind everyone else. Why does this keep happening?"
)

PASSAGES = [
    "Question: What should I do when the restlessness comes back?\n"
    "Answer: Let it come and notice that the noticing was already there before it arrived.",
]

GOOD_POINTING = (
    'You wrote "stuck", and you said it keeps happening. That sounds tiring to carry.\n\n'
    "Where is the feeling of being stuck right now?"
)

GOOD_EXPLANATORY = (
    "Self-inquiry means turning attention toward the sense of being yourself, instead of toward "
    "the thoughts about it. It is less a technique than a way of looking. You do not have to get "
    "anywhere with it."
)

GOOD_CRISIS = (
    "I read what you wrote, and I am glad you told me. Are you thinking of ending your life? "
    "I do not have the right number for where you are, so please contact your local emergency "
    "services or someone you trust now. I am staying here with you."
)

BAD = {
    "copies_background": (
        "Let it come, and notice that the noticing was already there before it arrived."
    ),
    "has_reference": "As chapter 4 explains, the restlessness is not the problem.",
    "quotes_source": 'Someone once said that "attention rests where it began." Try it now.',
    "names_listed_name": "Nisargadatta would ask you to stay with that feeling.",
    "has_list": "Try this:\n- notice the breath\n- notice the one noticing",
    "has_emoji": "It passes, and then it returns. \U0001F642",
    "has_bold_or_heading": "I am glad you told me. **Please contact emergency services now.**",
    "lacks_help": "I read what you wrote, and I am glad you said it. Are you thinking of ending "
    "your life?",
    "too_many_questions": "Where is it now? And who notices it?",
    "narrows_question": "What do you mean by hard? Is it the effort of it, or something else?",
    "text_after_question": "What is here when you sit? Not the quiet you remember. Just what is "
    "happening.",
    "over_word_limit_pointing": "word " * 301,
    "over_word_limit_explanatory": "word " * 451,
    "breaks_treatment_rule": "Stopping suddenly can be risky, so please talk to your doctor.",
    "invents_number": "I hear you. Please call 112 now. I am staying here with you.",
}
