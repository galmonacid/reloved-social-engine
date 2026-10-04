from reloved_engine.content import build_draft, validate_draft


def test_generated_draft_meets_contract():
    draft = build_draft("B_DONOR", "kettle", "moving flat", "It still worked.").as_dict()

    assert validate_draft(draft, "B_DONOR", "It still worked.") == []
    assert draft["market"] == "Milton Keynes, UK"
    assert draft["target_location"] == "Milton Keynes"
    assert "Milton Keynes" in draft["creative"]["slides"][4]
    assert "#MiltonKeynes" in draft["hashtags"]


def test_generated_drafts_use_pillar_specific_narrative_and_scene_plans():
    donor = build_draft("B_DONOR", "baby clothes bundle", "child outgrown them", "It still worked.").as_dict()
    finder = build_draft("C_FINDER", "kettle", "cost of living", "Why pay £60?").as_dict()

    assert donor["creative"]["slides"][2] == "I just did not need it anymore."
    assert donor["assets"]["scene_plan"] == ["FLAT", "FLAT", "FLAT", "FLAT", "STREET", "STREET"]
    assert finder["assets"]["scene_plan"] == ["FLAT", "SHOP", "STREET", "STREET", "FLAT", "FLAT"]


def test_validator_reports_contract_errors():
    draft = build_draft("B_DONOR", "kettle", "moving flat", "It still worked.").as_dict()
    draft["creative"]["slides"] = ["wrong"]
    draft["hashtags"] = ["not-a-tag"] * 6

    errors = validate_draft(draft, "UNKNOWN", "It still worked.")

    assert "creative.slides must contain exactly six strings" in errors
    assert "pillar is not supported" in errors
    assert "hashtags must contain at most five hash-prefixed strings" in errors


def test_validator_enforces_all_top_level_and_conciseness_rules():
    draft = build_draft("B_DONOR", "kettle", "moving flat", "It still worked.").as_dict()
    draft["language"] = "en-US"
    draft["pillar"] = "A_MACRO"
    draft["creative"]["slides"][1] = "x" * 70
    draft["caption"] = "\n".join(["line"] * 6)

    errors = validate_draft(draft, "B_DONOR", "It still worked.")

    assert "language must equal en-GB" in errors
    assert "pillar must equal B_DONOR" in errors
    assert "slides must be below 70 characters" in errors
    assert "caption must be a string containing at most five lines" in errors


def test_validator_requires_launch_location():
    draft = build_draft("B_DONOR", "kettle", "moving flat", "It still worked.").as_dict()
    draft["target_location"] = "London"

    errors = validate_draft(draft, "B_DONOR", "It still worked.")

    assert "target_location must equal Milton Keynes" in errors
