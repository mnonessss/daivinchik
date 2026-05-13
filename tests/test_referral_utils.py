import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from referral import build_referral_code, parse_referral_payload


def test_parse_referral_payload_success():
    assert parse_referral_payload("ref_42") == 42


def test_parse_referral_payload_invalid_values():
    assert parse_referral_payload(None) is None
    assert parse_referral_payload("") is None
    assert parse_referral_payload("foo") is None
    assert parse_referral_payload("ref_bar") is None
    assert parse_referral_payload("ref_-1") is None


def test_build_referral_code():
    assert build_referral_code(7) == "ref_7"
