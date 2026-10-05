from unittest.mock import patch

import unittest
from blackjack import Dealer, Hand, PlayerAgent, winners


class BlackjackTests(unittest.TestCase):
    def test_strict_under_21_and_ties(self):
        assert winners([Hand("a", [10, 10]), Hand("b", [9, 11]), Hand("c", [10, 11])]) == ["a", "b"]
        assert winners([Hand("a", [11, 11]), Hand("b", [])]) == []


    def test_only_dealer_draws_and_enforces_limit_and_turn(self):
        hands = {"a": Hand("a"), "b": Hand("b")}
        dealer = Dealer(hands)
        dealer.active = "a"
        with patch("blackjack.draw_card", return_value=2) as draw:
            with self.assertRaises(ValueError):
                dealer.request("b", "draw")
            assert draw.call_count == 0
            for _ in range(3):
                dealer.request("a", "draw")
            with self.assertRaises(ValueError):
                dealer.request("a", "draw")
            assert draw.call_count == 3


    def test_stand_and_ineligible_hand_cannot_draw(self):
        for action, cards in (("stand", []), ("draw", [10])):
            hand = Hand("a", cards)
            dealer = Dealer({"a": hand})
            dealer.active = "a"
            with patch("blackjack.draw_card", return_value=11):
                dealer.request("a", action)
                with self.assertRaises(ValueError):
                    dealer.request("a", "draw")


    def test_player_decision_does_not_invoke_tool(self):
        with patch("blackjack.draw_card") as draw:
            assert PlayerAgent(Hand("a", [5]), 16, "balanced").choose()["action"] == "draw"
            draw.assert_not_called()


    def test_natural_language_offline(self):
        dealer = Dealer({})
        assert dealer.interpret("deal me the next card") == "draw"
        assert dealer.interpret("I have enough") == "stand"
        assert dealer.interpret("hello") == "unknown"

if __name__ == "__main__":
    unittest.main()
