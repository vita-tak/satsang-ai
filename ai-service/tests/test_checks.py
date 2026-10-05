import pytest

from src.agent.checks import (
    CheckedReply,
    breaks_treatment_rule,
    copies_background,
    failed_checks,
    has_bold_or_heading,
    has_emoji,
    has_list,
    has_reference,
    invents_number,
    lacks_help,
    names_listed_name,
    narrows_question,
    over_word_limit,
    quotes_source,
    mentions_treatment,
    repeats_direction,
    too_many_questions,
)
from tests.data.replies import (
    BAD,
    GOOD_CRISIS,
    GOOD_EXPLANATORY,
    GOOD_POINTING,
    PASSAGES,
    PERSON_WORDS,
)
from tests.private_names import PRIVATE_NAMES

GOOD_REPLIES = [GOOD_POINTING, GOOD_EXPLANATORY, GOOD_CRISIS]


@pytest.mark.parametrize("reply", GOOD_REPLIES)
def test_good_replies_break_no_rule(reply: str) -> None:
    assert not copies_background(reply, PASSAGES)
    assert not has_reference(reply)
    assert not quotes_source(reply, PERSON_WORDS)
    assert not names_listed_name(reply, PERSON_WORDS, PRIVATE_NAMES)
    assert not has_list(reply)
    assert not has_emoji(reply)
    assert not has_bold_or_heading(reply)
    assert not too_many_questions(reply, PERSON_WORDS)


@pytest.mark.parametrize("reply", [GOOD_POINTING, GOOD_EXPLANATORY])
def test_good_pointing_and_explanatory_replies_do_not_narrow_a_question(reply: str) -> None:
    # Not run on crisis replies: part 5b has the guide stay after its direct question
    assert not narrows_question(reply, PERSON_WORDS)


def test_copies_background_fails_a_six_word_run_from_a_passage() -> None:
    assert copies_background(BAD["copies_background"], PASSAGES)


def test_copies_background_allows_five_shared_words() -> None:
    assert not copies_background("Notice that the noticing was there.", PASSAGES)


def test_has_reference_fails_a_numbered_reference() -> None:
    assert has_reference(BAD["has_reference"])


@pytest.mark.parametrize(
    "text", ["see Talk 107", "on page 12", "in ch. 5", "chapter iv", "\u00a7 3"]
)
def test_has_reference_finds_each_reference_form(text: str) -> None:
    assert has_reference(text)


@pytest.mark.parametrize(
    "text", ["In this section I look at the breath.", "This page of your life is open."]
)
def test_has_reference_ignores_ordinary_words(text: str) -> None:
    assert not has_reference(text)


def test_quotes_source_fails_a_quote_the_person_never_wrote() -> None:
    assert quotes_source(BAD["quotes_source"], PERSON_WORDS)


def test_quotes_source_fails_a_blockquote() -> None:
    assert quotes_source("> Attention rests where it began.\n\nTry it.", PERSON_WORDS)


def test_quotes_source_allows_the_persons_own_words_and_apostrophes() -> None:
    assert not quotes_source("You don't have to fix \u201cstuck\u201d today.", PERSON_WORDS)


def test_names_listed_name_fails_a_name_the_person_did_not_use() -> None:
    assert names_listed_name(BAD["names_listed_name"], PERSON_WORDS, PRIVATE_NAMES)


def test_names_listed_name_allows_a_name_the_person_used() -> None:
    person = "What did Nisargadatta say about fear?"
    reply = "I don't speak for Nisargadatta or any teacher, but fear itself can be looked at."
    assert not names_listed_name(reply, person, PRIVATE_NAMES)


def test_names_listed_name_needs_whole_words() -> None:
    assert not names_listed_name("The sun at its zenith.", PERSON_WORDS, ("Zen",))


def test_has_list_fails_bullets_and_numbers() -> None:
    assert has_list(BAD["has_list"])
    assert has_list("First this:\n1. look\n2. rest")


def test_has_list_ignores_a_sentence_that_starts_with_a_number() -> None:
    assert not has_list("2 weeks ago it started.")


def test_has_emoji_fails_an_emoji() -> None:
    assert has_emoji(BAD["has_emoji"])


def test_an_em_dash_is_allowed_in_a_reply() -> None:
    # The owner decided that em dashes in generated replies are fine
    assert not has_emoji("It passes \u2014 and then it returns.")


@pytest.mark.parametrize("text", [BAD["has_bold_or_heading"], "## Help\nCall now.", "__Now.__"])
def test_has_bold_or_heading_fails(text: str) -> None:
    assert has_bold_or_heading(text)


def test_lacks_help_fails_a_crisis_reply_that_points_nowhere() -> None:
    assert lacks_help(BAD["lacks_help"], [])


@pytest.mark.parametrize(
    "reply",
    [
        GOOD_CRISIS,
        "Please reach out to someone you trust tonight. I am staying here.",
        "Ring 11 22 now. I am here with you.",
        "Kontakta akuten eller n\u00e5gon du litar p\u00e5 nu.",
        "Ring n\u00f6dnumret nu. Jag \u00e4r h\u00e4r.",
        "Kontakta n\u00f6dnummer d\u00e4r du bor.",
        "Please talk with your doctor before you change anything.",
        "Prata med din l\u00e4kare innan du \u00e4ndrar n\u00e5got.",
    ],
)
def test_lacks_help_allows_a_reply_that_points_to_help(reply: str) -> None:
    assert not lacks_help(reply, ["11 22"])


def test_too_many_questions_fails_two_questions() -> None:
    assert too_many_questions(BAD["too_many_questions"], PERSON_WORDS)


def test_too_many_questions_ignores_the_persons_question_quoted_back() -> None:
    reply = 'You asked "Why does this keep happening?" What is here right now?'
    assert not too_many_questions(reply, PERSON_WORDS)


def test_narrows_question_fails_a_choice_inside_the_question() -> None:
    assert narrows_question(BAD["narrows_question"], PERSON_WORDS)


def test_narrows_question_fails_text_after_the_final_question_mark() -> None:
    assert narrows_question(BAD["text_after_question"], PERSON_WORDS)


@pytest.mark.parametrize(
    "reply",
    [
        "Where is it now? I am here.",
        "Where is it now?\n\nTake your time.",
        "That is what you see. What happens when you are simply with it? Nothing more.",
    ],
)
def test_narrows_question_finds_any_text_after_the_last_question(reply: str) -> None:
    assert narrows_question(reply, PERSON_WORDS)


@pytest.mark.parametrize(
    "reply",
    [
        "That is what you see.",
        "Where is it now?",
        'Where is the "stuck"?',
        "**Where is it now?**",
        "Where is it now? ",
        "You asked why this keeps happening. Where is it felt?\n",
    ],
)
def test_narrows_question_allows_a_reply_that_ends_on_its_question(reply: str) -> None:
    assert not narrows_question(reply, PERSON_WORDS)


def test_narrows_question_ignores_the_persons_own_question_quoted_back() -> None:
    person = "Why does this keep happening?"
    reply = 'You asked "Why does this keep happening?" Where is it felt?'
    assert not narrows_question(reply, person)


@pytest.mark.parametrize(
    "reply",
    [
        "Behind what, or behind whom?",
        "What do you mean by hard? Or somewhere else?",
        "K\u00e4nner du det tungt eller tr\u00f6gt, eller \u00e4r det n\u00e5got annat?",
        "What are you waiting for the shift to be, or to do?",
    ],
)
def test_narrows_question_finds_each_form(reply: str) -> None:
    assert narrows_question(reply, PERSON_WORDS)


@pytest.mark.parametrize(
    "reply",
    [
        "Where is the feeling of being stuck right now?",
        "You can stay or leave it as it is. What do you notice?",
        "What is it like when more of it comes?",
        'You said "stuck or slow". Where is that felt?',
    ],
)
def test_narrows_question_ignores_statements_other_words_and_the_persons_own(
    reply: str,
) -> None:
    person = 'I feel "stuck or slow" today.'
    assert not narrows_question(reply, person)


@pytest.mark.parametrize(
    ("situation", "key"),
    [("pointing", "over_word_limit_pointing"), ("explanatory", "over_word_limit_explanatory")],
)
def test_over_word_limit_fails_one_word_over_the_hard_limit(situation: str, key: str) -> None:
    assert over_word_limit(BAD[key], situation)


@pytest.mark.parametrize(("situation", "words"), [("pointing", 300), ("explanatory", 450)])
def test_over_word_limit_allows_the_hard_limit(situation: str, words: int) -> None:
    assert not over_word_limit("word " * words, situation)


def test_over_word_limit_sets_no_limit_for_social_replies() -> None:
    assert not over_word_limit("word " * 500, "social")


def test_repeats_direction_fails_a_direction_from_the_last_two() -> None:
    assert repeats_direction("Who", ["Who", "Change"])


@pytest.mark.parametrize("direction", ["Where", None])
def test_repeats_direction_allows_a_new_direction_or_no_turn(direction: str | None) -> None:
    assert not repeats_direction(direction, ["Who", "Change"])


def test_invents_number_fails_a_number_that_is_not_in_the_list() -> None:
    assert invents_number(BAD["invents_number"], [])


@pytest.mark.parametrize(
    "reply",
    [
        "Ring 112 nu.",
        "Ring SOS Alarm p\u00e5 112.",
        "Ring 112, eller kontakta n\u00e5gon du litar p\u00e5.",
        "N\u00f6dnumret \u00e4r 112",
        "Ring 1-1-2 nu.",
        "Ring 1 1 2 nu.",
        "Ring112",
        "tel:112",
        "Ring 90 101.",
        "Ring 1177.",
    ],
)
def test_invents_number_flags_any_digit_form_when_the_verified_list_is_empty(reply: str) -> None:
    assert invents_number(reply, [])


@pytest.mark.parametrize(
    "reply", ["Ring ett-ett-tv\u00e5.", "Call one one two.", "Ring etthundratolv."]
)
def test_invents_number_does_not_see_a_number_spelled_out_in_words(reply: str) -> None:
    # A known gap: only digits are read. lacks_help still decides whether it points to help.
    assert not invents_number(reply, [])


def test_invents_number_compares_digits_only_so_spacing_and_hyphens_do_not_matter() -> None:
    assert not invents_number("Ring 1-1-2 nu.", ["112"])
    assert not invents_number("Ring 90 101.", ["90101"])
    assert invents_number("Ring 112.", ["90101"])


def test_invents_number_flags_a_verified_number_run_into_a_longer_digit_run() -> None:
    assert invents_number("Ring 0771-90101.", ["90101"])


@pytest.mark.parametrize("text", ["It lasts 24 hours.", "Wait 5 minutes.", "Take 2 breaths."])
def test_invents_number_ignores_numbers_shorter_than_three_digits(text: str) -> None:
    assert not invents_number(text, [])


@pytest.mark.parametrize("text", ["In 2024 it changed.", "About 100 people."])
def test_invents_number_also_flags_any_other_run_of_three_digits(text: str) -> None:
    assert invents_number(text, [])


def test_invents_number_allows_numbers_from_the_list() -> None:
    assert not invents_number("You can call 90101 or 116 123 now.", ["90101", "116 123"])


def test_invents_number_allows_a_reply_without_numbers() -> None:
    assert not invents_number(GOOD_CRISIS, [])


def test_failed_checks_names_each_runtime_check_that_fails() -> None:
    reply = CheckedReply(
        text="As chapter 4 says, look. \U0001F642\n- here\n- there",
        situation="pointing",
        person_words=PERSON_WORDS,
        passages=tuple(PASSAGES),
    )
    assert failed_checks(reply) == ["has_reference", "has_list", "has_emoji"]


def test_failed_checks_reports_alternatives_for_pointing_and_explanatory_only() -> None:
    for situation, expected in [("pointing", True), ("explanatory", True), ("social", False)]:
        reply = CheckedReply(
            text=BAD["narrows_question"], situation=situation, person_words=PERSON_WORDS
        )
        assert ("narrows_question" in failed_checks(reply)) is expected


MEDICATION_MESSAGE = "Should I stop my antidepressants now that I meditate every day?"


def test_breaks_treatment_rule_fails_a_safety_word_about_a_treatment() -> None:
    assert breaks_treatment_rule(BAD["breaks_treatment_rule"], MEDICATION_MESSAGE)


@pytest.mark.parametrize(
    "reply",
    [
        "That is safe to do with your doctor.",
        "Is it done safely? Ask your prescriber.",
        "There is a risk in changing it alone.",
        "Some risks come with that. Ask your doctor.",
        "SAFE to ask, and RISKY to guess.",
    ],
)
def test_breaks_treatment_rule_finds_each_safety_word(reply: str) -> None:
    assert breaks_treatment_rule(reply, MEDICATION_MESSAGE)


@pytest.mark.parametrize(
    "reply",
    [
        "Meditation and medication work in different ways.",
        "Ask your doctor, and keep meditating if it helps.",
        "I cannot say how it relates to meditation.",
        "A meditator may feel this. Ask your doctor.",
        "MEDITATE less? Ask your doctor.",
    ],
)
def test_breaks_treatment_rule_finds_any_word_starting_with_meditat(reply: str) -> None:
    assert breaks_treatment_rule(reply, MEDICATION_MESSAGE)


@pytest.mark.parametrize(
    "reply",
    [
        "This is a question for your doctor or prescriber. I cannot answer it.",
        "That is a question for the doctor who knows you. How are you doing otherwise?",
        "Take safeguards with your doctor.",
        "An unsafe thing, a tricky one, in a premeditated way.",
        "Please ask your doctor about the mediation service too.",
    ],
)
def test_breaks_treatment_rule_allows_a_clean_reply_and_other_words(reply: str) -> None:
    assert not breaks_treatment_rule(reply, MEDICATION_MESSAGE)


def test_breaks_treatment_rule_ignores_a_message_that_is_not_about_a_treatment() -> None:
    reply = "It is risky to sit in the dark, and meditation can be safe."
    assert not breaks_treatment_rule(reply, "Is it safe to meditate in the dark?")


# What counts as a message about a treatment or medication. Checked by the owner: each row is a
# message and whether it is detected. The detector looks at the person's latest message only.
TREATMENT_MESSAGES = [
    # Words for medicines and treatments
    ("Should I stop my antidepressants now that I meditate every day?", True),
    ("I take a daily allergy tablet. Do I still need it?", True),
    ("My doctor prescribed a new treatment.", True),
    ("Can I come off my medication?", True),
    ("Should I change my dose?", True),
    ("I take my meds every morning.", True),
    ("I stopped my insulin last week.", True),
    ("I take sleeping pills.", True),
    ("Is chemotherapy something I can combine with this?", True),
    ("I started therapy last month.", True),
    ("My heart races at night. Should I stop my antidepressants?", True),
    # Drug names and groups added after round R7
    ("I have been on sertraline for a year.", True),
    ("Is fluoxetine making me tired?", True),
    ("My citalopram dose was raised.", True),
    ("Can I stop escitalopram?", True),
    ("I am on lithium.", True),
    ("I take ibuprofen most days for my back.", True),
    ("I take paracetamol for headaches.", True),
    ("I take acetaminophen for headaches.", True),
    ("Should I take an aspirin every day?", True),
    ("My SSRI makes me numb.", True),
    ("I take antibiotics for a chest infection.", True),
    ("I finished my antibiotic.", True),
    ("I take painkillers every evening.", True),
    ("My painkiller is wearing off.", True),
    ("I use my inhaler twice a day.", True),
    # Phrases
    ("I want to stop taking it.", True),
    ("I stopped taking them last week.", True),
    ("I am thinking of quitting taking them.", True),
    ("I quit taking it in March.", True),
    # Swedish
    ("Jag vill sluta med mina tabletter och min medicin.", True),
    ("Jag undrar om min behandling \u00e4r n\u00f6dv\u00e4ndig.", True),
    ("Kan jag sluta med mitt l\u00e4kemedel?", True),
    ("Jag tar sertralin varje morgon.", True),
    ("Jag tar litium.", True),
    ("Jag tar antibiotika just nu.", True),
    ("Jag har sm\u00e4rtstillande mot v\u00e4rk.", True),
    ("Jag vill sluta ta det.", True),
    ("Jag slutade ta dem i g\u00e5r.", True),
    # Over-detection the phrases cause: the message is not about a treatment, but is detected.
    # "stop taking" and "quit taking" cannot tell a medicine from anything else a person takes.
    ("I can't stop taking things personally.", True),
    ("I stop taking notes when I sit.", True),
    # Not about a treatment
    ("I feel stuck in my practice.", False),
    ("What does vichara mean?", False),
    ("Is it safe to meditate in the dark?", False),
    ("I keep taking things personally.", False),
    # "med" is the Swedish word for "with": it must never count on its own
    ("Jag vill vara med dig i min praktik.", False),
    ("Jag sitter med ett lugn idag.", False),
    ("Why do I take everything so hard?", False),
    # Treatment-related messages the detector still misses, because it has no word for them. They
    # are gaps, recorded as the current behaviour; widen the word list to close them.
    ("My blood pressure is high and I am worried.", False),
    ("My doctor said I need surgery.", False),
    ("Can I stop my vitamins?", False),
    ("I take metformin for my sugar.", False),
    # A short follow-up has no treatment word of its own: only the latest message is read
    ("Yes, I will do that.", False),
]


@pytest.mark.parametrize(("message", "detected"), TREATMENT_MESSAGES)
def test_mentions_treatment_detects_what_the_owner_expects(message: str, detected: bool) -> None:
    assert mentions_treatment(message) is detected


@pytest.mark.parametrize("situation", ["pointing", "explanatory", "crisis"])
def test_failed_checks_reports_the_treatment_rule(situation: str) -> None:
    reply = CheckedReply(
        text=BAD["breaks_treatment_rule"], situation=situation, message=MEDICATION_MESSAGE
    )
    assert "breaks_treatment_rule" in failed_checks(reply)


def test_failed_checks_leaves_social_replies_and_other_messages_alone() -> None:
    social = CheckedReply(
        text=BAD["breaks_treatment_rule"], situation="social", message=MEDICATION_MESSAGE
    )
    other = CheckedReply(
        text=BAD["breaks_treatment_rule"], situation="pointing", message="I feel stuck."
    )
    assert failed_checks(social) == []
    assert "breaks_treatment_rule" not in failed_checks(other)


def test_failed_checks_reports_a_repeated_direction() -> None:
    reply = CheckedReply(
        text=GOOD_POINTING,
        situation="pointing",
        person_words=PERSON_WORDS,
        direction="Where",
        recent_directions=("Where", "Who"),
    )
    assert failed_checks(reply) == ["repeats_direction"]


def test_failed_checks_runs_the_crisis_checks_on_crisis_replies() -> None:
    # An invented number is no help either, so both checks fail
    reply = CheckedReply(text=BAD["invents_number"], situation="crisis")
    assert failed_checks(reply) == ["invents_number", "lacks_help"]


def test_failed_checks_reports_a_crisis_reply_without_help_and_with_bold() -> None:
    reply = CheckedReply(text="**I am here.** Are you safe?", situation="crisis")
    assert failed_checks(reply) == ["lacks_help", "has_bold_or_heading"]


def test_failed_checks_passes_good_replies() -> None:
    pointing = CheckedReply(
        text=GOOD_POINTING,
        situation="pointing",
        person_words=PERSON_WORDS,
        passages=tuple(PASSAGES),
    )
    crisis = CheckedReply(text=GOOD_CRISIS, situation="crisis")
    assert failed_checks(pointing) == []
    assert failed_checks(crisis) == []


def test_failed_checks_skips_social_replies() -> None:
    assert failed_checks(CheckedReply(text=BAD["has_list"], situation="social")) == []
