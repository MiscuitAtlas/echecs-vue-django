"""Règles du jeu d'échecs, sans dépendance : le serveur s'en sert pour valider chaque coup."""

from .game import Game, IllegalMove, Outcome, PlayedMove
from .position import START_FEN, Move, Position, parse_square, square_name

__all__ = [
    "START_FEN",
    "Game",
    "IllegalMove",
    "Move",
    "Outcome",
    "PlayedMove",
    "Position",
    "parse_square",
    "square_name",
]
