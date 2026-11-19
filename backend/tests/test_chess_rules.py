"""Règles des échecs, sans Django."""

import pytest

from chess_rules import START_FEN, Game, IllegalMove, Move, Position


def perft(position: Position, depth: int) -> int:
    """Nombre de positions atteignables en `depth` demi-coups : la façon classique de vérifier
    un générateur de coups, en comparant à des valeurs de référence publiées."""
    moves = position.legal_moves()
    if depth == 1:
        return len(moves)
    return sum(perft(position.push(move), depth - 1) for move in moves)


# Positions de référence du Chess Programming Wiki (page « Perft Results »).
PERFT = [
    pytest.param(START_FEN, [20, 400, 8902], id="position initiale"),
    pytest.param(
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        [48, 2039],
        id="kiwipete : roques, prises en passant, clouages",
    ),
    pytest.param(
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", [14, 191, 2812], id="finale : prise en passant et échecs"
    ),
    pytest.param("r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", [6, 264, 9467], id="promotions"),
    pytest.param("rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", [44, 1486], id="promotion avec prise"),
    pytest.param(
        "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10", [46, 2079], id="milieu de partie"
    ),
]


@pytest.mark.parametrize(("fen", "expected"), PERFT)
def test_move_generation_matches_reference_counts(fen, expected):
    position = Position.from_fen(fen)
    assert [perft(position, depth) for depth in range(1, len(expected) + 1)] == expected


@pytest.mark.parametrize("fen", [param.values[0] for param in PERFT])
def test_fen_round_trip(fen):
    assert Position.from_fen(fen).fen() == fen


@pytest.mark.parametrize(
    "fen", ["", "8/8/8/8/8/8/8 w - - 0 1", "9/8/8/8/8/8/8/8 w - - 0 1", START_FEN.replace(" w ", " x ")]
)
def test_invalid_fen_is_refused(fen):
    with pytest.raises(ValueError):
        Position.from_fen(fen)


def play(*moves: str) -> Game:
    game = Game()
    for move in moves:
        game.play(move)
    return game


def test_standard_algebraic_notation():
    game = play("e2e4", "d7d5", "e4d5", "d8d5", "b1c3", "d5a5", "d2d4", "c7c6", "g1f3", "c8g4", "f1e2", "e7e6")
    assert game.sans() == ["e4", "d5", "exd5", "Qxd5", "Nc3", "Qa5", "d4", "c6", "Nf3", "Bg4", "Be2", "e6"]
    castle = game.play("e1g1")
    assert castle.san == "O-O"


def test_notation_names_the_right_piece_when_two_can_move_there():
    # Deux cavaliers peuvent aller en d2 : on précise la colonne de départ.
    position = Position.from_fen("4k3/8/8/8/8/5N2/8/1N2K3 w - - 0 1")
    assert position.san(Move.from_uci("b1d2")) == "Nbd2"
    # Deux tours sur la même colonne : on précise la rangée.
    position = Position.from_fen("4k3/R7/8/8/8/8/R7/4K3 w - - 0 1")
    assert position.san(Move.from_uci("a2a5")) == "R2a5"


def test_promotion_check_and_mate_in_notation():
    position = Position.from_fen("4k3/1P6/8/8/8/8/8/4K3 w - - 0 1")
    assert position.san(Move.from_uci("b7b8q")) == "b8=Q+"
    assert position.san(Move.from_uci("b7b8n")) == "b8=N"
    game = play("f2f3", "e7e5", "g2g4")
    assert game.play("d8h4").san == "Qh4#"


def test_castling_is_refused_through_check_or_after_the_king_moved():
    # La case f1 est attaquée par le fou en c4 : pas de petit roque.
    position = Position.from_fen("4k3/8/8/8/2b5/8/8/4K2R w K - 0 1")
    assert Move.from_uci("e1g1") not in position.legal_moves()
    # Le roi a bougé puis est revenu : le roque n'est plus possible.
    game = Game(start_fen="4k3/8/8/8/8/8/8/R3K2R w KQ - 0 1")
    for move in ["e1e2", "e8e7", "e2e1", "e7e8"]:
        game.play(move)
    assert game.position.castling == ""
    # Une tour prise sur sa case de départ fait perdre le roque de ce côté.
    game = Game(start_fen="r3k3/8/8/8/8/8/8/R3K2R b KQq - 0 1")
    game.play("a8a1")
    assert game.position.castling == "K"


def test_en_passant_only_right_after_the_double_step():
    game = play("e2e4", "a7a6", "e4e5", "d7d5")
    assert "e5d6" in [move.uci() for move in game.legal_moves()]
    played = game.play("e5d6")
    assert played.san == "exd6"
    assert game.position.board[35] is None  # le pion noir de d5 a disparu

    game = play("e2e4", "a7a6", "e4e5", "d7d5", "h2h3", "h7h6")
    assert "e5d6" not in [move.uci() for move in game.legal_moves()]


def test_a_pinned_piece_cannot_move():
    # Le cavalier e2 est cloué par la tour e8 devant son roi.
    position = Position.from_fen("4r1k1/8/8/8/8/8/4N3/4K3 w - - 0 1")
    assert all(move.from_square != 12 for move in position.legal_moves())


def test_illegal_moves_are_refused_with_a_reason():
    game = Game()
    with pytest.raises(IllegalMove, match="pas autorisé"):
        game.play("e2e5")
    with pytest.raises(IllegalMove, match="mal écrit"):
        game.play("z9e4")
    with pytest.raises(IllegalMove, match="pas autorisé"):
        game.play("e7e5")  # pion noir, aux blancs de jouer
    game = Game(start_fen="4k3/1P6/8/8/8/8/8/4K3 w - - 0 1")
    with pytest.raises(IllegalMove, match="promotion"):
        game.play("b7b8")


def test_checkmate_ends_the_game():
    game = play("f2f3", "e7e5", "g2g4", "d8h4")
    assert (game.outcome().result, game.outcome().reason) == ("0-1", "mat")
    assert game.legal_moves() == []
    with pytest.raises(IllegalMove, match="terminée"):
        game.play("a2a3")


def test_stalemate_is_a_draw():
    game = Game(start_fen="7k/8/6Q1/8/8/8/8/K7 b - - 0 1")
    assert (game.outcome().result, game.outcome().reason) == ("1/2-1/2", "pat")


@pytest.mark.parametrize(
    ("fen", "insufficient"),
    [
        ("4k3/8/8/8/8/8/8/4K3 w - - 0 1", True),
        ("4k3/8/8/8/8/8/8/2B1K3 w - - 0 1", True),
        ("4k3/8/8/8/8/8/8/1N2K3 w - - 0 1", True),
        ("2b1k3/8/8/8/8/8/8/2B1K3 w - - 0 1", False),  # fous de couleurs différentes
        ("3bk3/8/8/8/8/8/8/2B1K3 w - - 0 1", True),  # fous sur la même couleur
        ("4k3/8/8/8/8/8/8/1NN1K3 w - - 0 1", False),
        ("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1", False),
    ],
)
def test_insufficient_material(fen, insufficient):
    assert Position.from_fen(fen).has_insufficient_material() is insufficient


def test_threefold_repetition_is_a_draw():
    game = Game()
    for _ in range(2):
        for move in ["g1f3", "g8f6", "f3g1", "f6g8"]:
            assert game.outcome() is None
            game.play(move)
    assert (game.outcome().result, game.outcome().reason) == ("1/2-1/2", "repetition")


def test_fifty_move_rule():
    game = Game(start_fen="4k3/8/8/8/8/8/8/R3K3 w - - 99 80")
    assert game.outcome() is None
    game.play("a1a2")
    assert game.outcome().reason == "cinquante_coups"
    # Un coup de pion remet le compteur à zéro.
    game = Game(start_fen="4k3/8/8/8/8/8/P7/R3K3 w - - 99 80")
    game.play("a2a3")
    assert game.outcome() is None


def test_moves_can_be_replayed_from_their_coordinates():
    game = play("e2e4", "e7e5", "g1f3")
    replayed = Game(game.moves)
    assert (
        replayed.position.fen()
        == game.position.fen()
        == ("rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2")
    )
