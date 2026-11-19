"""Position d'échecs : placement des pièces, coups légaux et notation.

L'échiquier est une liste de 64 cases, de a1 (0) à h8 (63) : case = rangée * 8 + colonne.
Les pièces sont notées comme en FEN : majuscules pour les blancs (PNBRQK), minuscules pour
les noirs. Une case vide vaut None.

Ce module ne dépend que de la bibliothèque standard : il sert au serveur pour valider
chaque coup, et ses tests le comparent aux décomptes de référence (perft).
"""

from __future__ import annotations

from dataclasses import dataclass

FILES = "abcdefgh"
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
WHITE, BLACK = "w", "b"
PROMOTIONS = ("q", "r", "b", "n")


def square_name(square: int) -> str:
    return FILES[square % 8] + str(square // 8 + 1)


def parse_square(name: str) -> int:
    if len(name) != 2 or name[0] not in FILES or name[1] not in "12345678":
        raise ValueError(f"Case invalide : {name!r}")
    return (int(name[1]) - 1) * 8 + FILES.index(name[0])


def color_of(piece: str) -> str:
    return WHITE if piece.isupper() else BLACK


def opponent(color: str) -> str:
    return BLACK if color == WHITE else WHITE


def _targets(steps: list[tuple[int, int]]) -> list[list[int]]:
    """Cases atteintes en un pas depuis chaque case (cavalier, roi)."""
    table = []
    for square in range(64):
        file, rank = square % 8, square // 8
        table.append([(rank + dr) * 8 + file + df for df, dr in steps if 0 <= file + df < 8 and 0 <= rank + dr < 8])
    return table


def _rays(directions: list[tuple[int, int]]) -> list[list[list[int]]]:
    """Pour chaque case, la liste des cases dans chaque direction, de la plus proche à la plus loin."""
    table = []
    for square in range(64):
        file, rank = square % 8, square // 8
        rays = []
        for df, dr in directions:
            ray, f, r = [], file + df, rank + dr
            while 0 <= f < 8 and 0 <= r < 8:
                ray.append(r * 8 + f)
                f, r = f + df, r + dr
            rays.append(ray)
        table.append(rays)
    return table


KNIGHT_TARGETS = _targets([(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)])
KING_TARGETS = _targets([(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)])
ROOK_RAYS = _rays([(1, 0), (-1, 0), (0, 1), (0, -1)])
BISHOP_RAYS = _rays([(1, 1), (1, -1), (-1, 1), (-1, -1)])

# Coins des tours : un roque disparaît quand sa tour bouge ou y est prise.
ROOK_CORNERS = {0: "Q", 7: "K", 56: "q", 63: "k"}
E1, G1, C1, E8, G8, C8 = 4, 6, 2, 60, 62, 58


@dataclass(frozen=True)
class Move:
    """Coup en coordonnées : case de départ, case d'arrivée, pièce de promotion éventuelle."""

    from_square: int
    to_square: int
    promotion: str | None = None

    @classmethod
    def from_uci(cls, text: str) -> Move:
        """« e2e4 », « e7e8q » : la notation des coups échangée avec le navigateur."""
        if not isinstance(text, str) or len(text) not in (4, 5):
            raise ValueError(f"Coup invalide : {text!r}")
        promotion = text[4] if len(text) == 5 else None
        if promotion is not None and promotion not in PROMOTIONS:
            raise ValueError(f"Promotion invalide : {text!r}")
        return cls(parse_square(text[:2]), parse_square(text[2:4]), promotion)

    def uci(self) -> str:
        return square_name(self.from_square) + square_name(self.to_square) + (self.promotion or "")


class Position:
    __slots__ = ("board", "castling", "ep_square", "fullmove", "halfmove", "turn")

    def __init__(
        self,
        board: list[str | None],
        turn: str,
        castling: str,
        ep_square: int | None,
        halfmove: int,
        fullmove: int,
    ) -> None:
        self.board = board
        self.turn = turn
        self.castling = castling
        self.ep_square = ep_square
        self.halfmove = halfmove
        self.fullmove = fullmove

    # --- FEN -------------------------------------------------------------------------------

    @classmethod
    def initial(cls) -> Position:
        return cls.from_fen(START_FEN)

    @classmethod
    def from_fen(cls, fen: str) -> Position:
        fields = fen.split()
        if len(fields) != 6:
            raise ValueError("FEN invalide : six champs attendus.")
        placement, turn, castling, ep, halfmove, fullmove = fields
        ranks = placement.split("/")
        if len(ranks) != 8:
            raise ValueError("FEN invalide : huit rangées attendues.")
        board: list[str | None] = [None] * 64
        for index, row in enumerate(ranks):
            rank = 7 - index
            file = 0
            for char in row:
                if char.isdigit():
                    file += int(char)
                elif char in "PNBRQKpnbrqk" and file < 8:
                    board[rank * 8 + file] = char
                    file += 1
                else:
                    raise ValueError(f"FEN invalide : {char!r}")
            if file != 8:
                raise ValueError("FEN invalide : rangée incomplète.")
        if turn not in (WHITE, BLACK) or any(c not in "KQkq" for c in castling.replace("-", "")):
            raise ValueError("FEN invalide : trait ou roques.")
        return cls(
            board,
            turn,
            "" if castling == "-" else castling,
            None if ep == "-" else parse_square(ep),
            int(halfmove),
            int(fullmove),
        )

    def placement(self) -> str:
        rows = []
        for rank in range(7, -1, -1):
            row, empty = "", 0
            for file in range(8):
                piece = self.board[rank * 8 + file]
                if piece is None:
                    empty += 1
                else:
                    row += (str(empty) if empty else "") + piece
                    empty = 0
            rows.append(row + (str(empty) if empty else ""))
        return "/".join(rows)

    def fen(self) -> str:
        ep = square_name(self.ep_square) if self.ep_square is not None else "-"
        return f"{self.placement()} {self.turn} {self.castling or '-'} {ep} {self.halfmove} {self.fullmove}"

    # --- Attaques --------------------------------------------------------------------------

    def king_square(self, color: str) -> int | None:
        king = "K" if color == WHITE else "k"
        for square, piece in enumerate(self.board):
            if piece == king:
                return square
        return None

    def is_attacked(self, square: int, by: str) -> bool:
        """La case est-elle attaquée par une pièce de la couleur `by` ?"""
        board = self.board
        white = by == WHITE
        # Pions : on regarde d'où un pion de l'attaquant pourrait prendre sur cette case.
        file = square % 8
        pawn, behind = ("P", -8) if white else ("p", 8)
        for df in (-1, 1):
            if 0 <= file + df < 8:
                origin = square + behind + df
                if 0 <= origin < 64 and board[origin] == pawn:
                    return True
        knight, king = ("N", "K") if white else ("n", "k")
        if any(board[t] == knight for t in KNIGHT_TARGETS[square]):
            return True
        if any(board[t] == king for t in KING_TARGETS[square]):
            return True
        straight, diagonal = ("RQ", "BQ") if white else ("rq", "bq")
        for rays, attackers in ((ROOK_RAYS[square], straight), (BISHOP_RAYS[square], diagonal)):
            for ray in rays:
                for target in ray:
                    piece = board[target]
                    if piece is not None:
                        if piece in attackers:
                            return True
                        break
        return False

    def in_check(self, color: str | None = None) -> bool:
        color = color or self.turn
        king = self.king_square(color)
        return king is not None and self.is_attacked(king, opponent(color))

    # --- Génération des coups --------------------------------------------------------------

    def pseudo_legal_moves(self) -> list[Move]:
        """Coups qui respectent la marche des pièces, sans vérifier si le roi reste en prise."""
        moves: list[Move] = []
        board, turn = self.board, self.turn
        for square, piece in enumerate(board):
            if piece is None or color_of(piece) != turn:
                continue
            kind = piece.lower()
            if kind == "p":
                self._pawn_moves(square, moves)
            elif kind == "n":
                for target in KNIGHT_TARGETS[square]:
                    occupant = board[target]
                    if occupant is None or color_of(occupant) != turn:
                        moves.append(Move(square, target))
            elif kind == "k":
                for target in KING_TARGETS[square]:
                    occupant = board[target]
                    if occupant is None or color_of(occupant) != turn:
                        moves.append(Move(square, target))
                self._castling_moves(square, moves)
            else:
                rays = []
                if kind in "rq":
                    rays += ROOK_RAYS[square]
                if kind in "bq":
                    rays += BISHOP_RAYS[square]
                for ray in rays:
                    for target in ray:
                        occupant = board[target]
                        if occupant is None:
                            moves.append(Move(square, target))
                            continue
                        if color_of(occupant) != turn:
                            moves.append(Move(square, target))
                        break
        return moves

    def _pawn_moves(self, square: int, moves: list[Move]) -> None:
        board, turn = self.board, self.turn
        step, start_rank, last_rank = (8, 1, 7) if turn == WHITE else (-8, 6, 0)
        file, rank = square % 8, square // 8

        def add(target: int) -> None:
            if target // 8 == last_rank:
                moves.extend(Move(square, target, promotion) for promotion in PROMOTIONS)
            else:
                moves.append(Move(square, target))

        forward = square + step
        if 0 <= forward < 64 and board[forward] is None:
            add(forward)
            double = forward + step
            if rank == start_rank and board[double] is None:
                moves.append(Move(square, double))
        for df in (-1, 1):
            if not 0 <= file + df < 8:
                continue
            target = forward + df
            if not 0 <= target < 64:
                continue
            occupant = board[target]
            if occupant is not None and color_of(occupant) != turn:
                add(target)
            elif target == self.ep_square:
                moves.append(Move(square, target))

    def _castling_moves(self, square: int, moves: list[Move]) -> None:
        board, turn = self.board, self.turn
        if turn == WHITE:
            king_start, rights, rook = E1, ("K", "Q"), "R"
        else:
            king_start, rights, rook = E8, ("k", "q"), "r"
        if square != king_start or not self.castling:
            return
        enemy = opponent(turn)
        if self.is_attacked(king_start, enemy):
            return
        # Petit roque : f et g vides, non attaquées ; grand roque : b, c et d vides, c et d non attaquées.
        if rights[0] in self.castling and board[king_start + 3] == rook:
            path = (king_start + 1, king_start + 2)
            if all(board[s] is None for s in path) and not any(self.is_attacked(s, enemy) for s in path):
                moves.append(Move(king_start, king_start + 2))
        if rights[1] in self.castling and board[king_start - 4] == rook:
            empty = (king_start - 1, king_start - 2, king_start - 3)
            safe = (king_start - 1, king_start - 2)
            if all(board[s] is None for s in empty) and not any(self.is_attacked(s, enemy) for s in safe):
                moves.append(Move(king_start, king_start - 2))

    def legal_moves(self) -> list[Move]:
        turn = self.turn
        return [move for move in self.pseudo_legal_moves() if not self.push(move).in_check(turn)]

    def is_legal(self, move: Move) -> bool:
        return move in self.legal_moves()

    # --- Jouer un coup ---------------------------------------------------------------------

    def push(self, move: Move) -> Position:
        """Nouvelle position après le coup, supposé pseudo-légal. La position actuelle ne change pas."""
        board = self.board.copy()
        piece = board[move.from_square]
        if piece is None:
            raise ValueError("Aucune pièce sur la case de départ.")
        captured = board[move.to_square]
        kind = piece.lower()
        castling = self.castling
        ep_square = None

        board[move.to_square] = piece
        board[move.from_square] = None

        if kind == "p":
            if move.to_square == self.ep_square and captured is None and move.from_square % 8 != move.to_square % 8:
                # Prise en passant : le pion pris est à côté, pas sur la case d'arrivée.
                captured_square = move.to_square + (-8 if self.turn == WHITE else 8)
                captured = board[captured_square]
                board[captured_square] = None
            if abs(move.to_square - move.from_square) == 16:
                ep_square = (move.from_square + move.to_square) // 2
            if move.promotion:
                board[move.to_square] = move.promotion.upper() if self.turn == WHITE else move.promotion
        elif kind == "k":
            lost = "KQ" if self.turn == WHITE else "kq"
            castling = "".join(right for right in castling if right not in lost)
            if move.to_square - move.from_square == 2:
                board[move.from_square + 1], board[move.from_square + 3] = board[move.from_square + 3], None
            elif move.from_square - move.to_square == 2:
                board[move.from_square - 1], board[move.from_square - 4] = board[move.from_square - 4], None

        for corner in (move.from_square, move.to_square):
            if corner in ROOK_CORNERS:
                castling = castling.replace(ROOK_CORNERS[corner], "")

        return Position(
            board,
            opponent(self.turn),
            castling,
            ep_square,
            0 if kind == "p" or captured is not None else self.halfmove + 1,
            self.fullmove + (1 if self.turn == BLACK else 0),
        )

    # --- Fins de partie et répétitions -----------------------------------------------------

    def repetition_key(self) -> str:
        """Ce qui fait qu'une position est « la même » pour la règle des trois répétitions :
        pièces, trait, roques, et case de prise en passant seulement si la prise est possible."""
        ep = "-"
        if self.ep_square is not None and any(
            move.to_square == self.ep_square and (self.board[move.from_square] or "").lower() == "p"
            for move in self.legal_moves()
        ):
            ep = square_name(self.ep_square)
        return f"{self.placement()} {self.turn} {self.castling or '-'} {ep}"

    def has_insufficient_material(self) -> bool:
        """Aucun mat possible : rois seuls, un fou ou un cavalier en plus, ou des fous tous sur la même couleur."""
        minors = []
        for square, piece in enumerate(self.board):
            if piece is None or piece in "Kk":
                continue
            if piece in "PpRrQq":
                return False
            minors.append((piece, square))
        if len(minors) <= 1:
            return True
        if all(piece in "Bb" for piece, _ in minors):
            colors = {(square % 8 + square // 8) % 2 for _, square in minors}
            return len(colors) == 1
        return False

    # --- Notation algébrique ---------------------------------------------------------------

    def san(self, move: Move) -> str:
        """Notation algébrique standard (« Nf3 », « exd5 », « O-O », « e8=Q+ ») d'un coup légal."""
        piece = self.board[move.from_square]
        if piece is None:
            raise ValueError("Aucune pièce sur la case de départ.")
        kind = piece.lower()
        target = square_name(move.to_square)
        if kind == "k" and abs(move.to_square - move.from_square) == 2:
            text = "O-O" if move.to_square > move.from_square else "O-O-O"
        elif kind == "p":
            capture = move.from_square % 8 != move.to_square % 8
            text = (FILES[move.from_square % 8] + "x" if capture else "") + target
            if move.promotion:
                text += "=" + move.promotion.upper()
        else:
            capture = self.board[move.to_square] is not None
            rivals = [
                other.from_square
                for other in self.legal_moves()
                if other.to_square == move.to_square
                and other.from_square != move.from_square
                and self.board[other.from_square] == piece
            ]
            hint = ""
            if rivals:
                file, rank = move.from_square % 8, move.from_square // 8
                if all(r % 8 != file for r in rivals):
                    hint = FILES[file]
                elif all(r // 8 != rank for r in rivals):
                    hint = str(rank + 1)
                else:
                    hint = square_name(move.from_square)
            text = kind.upper() + hint + ("x" if capture else "") + target
        after = self.push(move)
        if after.in_check():
            text += "#" if not after.legal_moves() else "+"
        return text
