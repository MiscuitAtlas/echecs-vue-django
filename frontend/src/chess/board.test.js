import { describe, expect, it } from 'vitest'
import { applyMove, boardToFen, displayOrder, frenchSan, parseFen, pieceLabel, squareIndex, squareName } from './board.js'

const START = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

describe('position', () => {
  it('lit la FEN case par case', () => {
    const board = parseFen(START)
    expect(board[squareIndex('e1')]).toBe('K')
    expect(board[squareIndex('d8')]).toBe('q')
    expect(board.filter(Boolean)).toHaveLength(32)
    expect(squareName(squareIndex('g7'))).toBe('g7')
    expect(boardToFen(board).split(' ')[0]).toBe(START.split(' ')[0])
  })

  it('applique le roque, la prise en passant et la promotion', () => {
    let board = parseFen('r3k2r/8/8/3pP3/8/8/1p6/R3K2R w KQkq d6 0 1')
    board = applyMove(board, 'e1g1')
    expect([board[squareIndex('g1')], board[squareIndex('f1')], board[squareIndex('h1')]]).toEqual(['K', 'R', null])
    board = applyMove(board, 'e5d6')
    expect([board[squareIndex('d6')], board[squareIndex('d5')]]).toEqual(['P', null])
    board = applyMove(board, 'b2b1n')
    expect(board[squareIndex('b1')]).toBe('n')
  })

  it("retourne l'échiquier pour les Noirs", () => {
    expect(displayOrder('w').slice(0, 2).map(squareName)).toEqual(['a8', 'b8'])
    expect(displayOrder('b').slice(0, 2).map(squareName)).toEqual(['h1', 'g1'])
  })

  it('nomme les pièces avec le bon accord', () => {
    expect(['Q', 'r', 'N', 'p'].map(pieceLabel)).toEqual(['dame blanche', 'tour noire', 'cavalier blanc', 'pion noir'])
  })

  it('traduit la notation en français', () => {
    expect(frenchSan('Nxe5+')).toBe('Cxe5+')
    expect(frenchSan('exd8=Q#')).toBe('exd8=D#')
    expect(frenchSan('O-O')).toBe('O-O')
  })
})
