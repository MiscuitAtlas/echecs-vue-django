"""Déroulement d'une partie : coups joués, notation, répétitions et fin de partie."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from .position import START_FEN, WHITE, Move, Position


class IllegalMove(ValueError):
    """Coup refusé : mal écrit, ou interdit dans la position."""


@dataclass(frozen=True)
class PlayedMove:
    uci: str
    san: str
    fen: str


@dataclass(frozen=True)
class Outcome:
    result: str  # « 1-0 », « 0-1 » ou « 1/2-1/2 »
    reason: str  # mat, pat, repetition, cinquante_coups, materiel


class Game:
    """Partie rejouée à partir de ses coups. Les coups enregistrés ont déjà été validés :
    ils sont rejoués sans revérifier leur légalité, seul un nouveau coup est contrôlé."""

    def __init__(self, moves: Iterable[str] = (), start_fen: str = START_FEN) -> None:
        self.start_fen = start_fen
        self.position = Position.from_fen(start_fen)
        self.moves: list[str] = []
        self.repetitions: Counter[str] = Counter([self.position.repetition_key()])
        for uci in moves:
            self._push(Move.from_uci(uci))

    def _push(self, move: Move) -> None:
        self.position = self.position.push(move)
        self.moves.append(move.uci())
        self.repetitions[self.position.repetition_key()] += 1

    @property
    def turn(self) -> str:
        return self.position.turn

    def legal_moves(self) -> list[Move]:
        return [] if self.outcome() is not None else self.position.legal_moves()

    def play(self, uci: str) -> PlayedMove:
        """Joue un coup reçu du navigateur, après avoir vérifié qu'il est légal."""
        if self.outcome() is not None:
            raise IllegalMove("La partie est terminée.")
        try:
            move = Move.from_uci(uci)
        except ValueError as error:
            raise IllegalMove("Coup mal écrit.") from error
        legal = self.position.legal_moves()
        if move not in legal:
            # Un pion qui atteint la dernière rangée doit préciser sa promotion.
            if move.promotion is None and Move(move.from_square, move.to_square, "q") in legal:
                raise IllegalMove("Choisissez la pièce de promotion.")
            raise IllegalMove("Ce coup n'est pas autorisé dans cette position.")
        san = self.position.san(move)
        self._push(move)
        return PlayedMove(move.uci(), san, self.position.fen())

    def outcome(self) -> Outcome | None:
        """Fin automatique de la partie, ou None si elle continue.

        Comme sur la plupart des sites d'échecs, la triple répétition et la règle des
        cinquante coups terminent la partie sans qu'un joueur ait à la réclamer."""
        position = self.position
        if not position.legal_moves():
            if position.in_check():
                return Outcome("0-1" if position.turn == WHITE else "1-0", "mat")
            return Outcome("1/2-1/2", "pat")
        if position.has_insufficient_material():
            return Outcome("1/2-1/2", "materiel")
        if self.repetitions[position.repetition_key()] >= 3:
            return Outcome("1/2-1/2", "repetition")
        if position.halfmove >= 100:
            return Outcome("1/2-1/2", "cinquante_coups")
        return None

    def sans(self) -> list[str]:
        """Notation algébrique de tous les coups, en rejouant la partie depuis le début."""
        position = Position.from_fen(self.start_fen)
        notation = []
        for uci in self.moves:
            move = Move.from_uci(uci)
            notation.append(position.san(move))
            position = position.push(move)
        return notation
