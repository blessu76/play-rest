---
slug: 2026-11-19-should-a-game-let-you-take-it-back
lang: en
title: "Should a game let you take it back?"
alt_title: "물러 주는 게임, 안 물러 주는 게임"
description: "An undo button is kind to a clumsy thumb and bad for a weighty decision. The case for and against taking a move back in a short turn-based game."
excerpt: "Why undo is a real design choice, what it protects you from, and what it quietly takes away."
published_at: 2026-11-19T12:44+09:00
category: games
original: en
author: ipe()
keywords: undo button, take back move, game design, turn-based games, touch controls, casual strategy, ipe() games
---

Every turn-based game on a phone eventually meets the same small button. Should you be able to undo your last move?

Both answers are defensible, and which one is right depends on what the move is worth.

## The case for undo

On a touch screen, a thumb slips. You meant to tap one square and tapped its neighbor. That is not a decision you made badly. It is a mistake of the hand, and punishing it feels unfair in a way that no clever rule can make up for.

A break also gets interrupted. If the bus lurches halfway through a move, being able to take it back is a kindness. Undo can also make a game easier to learn: when a mistake costs nothing, you are freer to try something odd and see what happens.

## The case against

There is a cost on the other side, and it is the weight of the move. In a game where your choice matters, the choice matters partly because you cannot take it back. If you can always undo, you can always peek. You try the move, see how the opponent answers, rewind, and play the better one. The game stops asking you to decide and starts asking you to test.

That is especially true when part of the board is hidden. An undo after a look at the fog changes what the fog means.

## Middle roads

Games that care about both sides tend to settle between the two. One option is to allow undo only until the other side has acted, which protects against slips without giving you a free look at the future. Another is to ask for confirmation on a move that cannot be undone, so the slip is stopped before it happens. A third is to make the weighty moves hard to do by accident, such as a drag that has to end somewhere.

None of these is perfect. A confirmation tap on every move turns a quick game into a slow one, which is a poor trade in a break.

## Where we stand

We should be careful here, because the sites of our four games do not describe an undo button, and we do not want to invent one. What we can say is how we think about it. In [Sunmeld](https://sunmeld.ipe.rest), whoever overflows the tub loses, and that makes the last stone a real decision. A game with an ending that sharp gains from moves that count, and we would want any softening of it to be a considered choice, not a default.

For the same reason, a slip should not decide a match. That tension is real and we have not resolved it in writing. Our games are not released, and how they treat a mistaken tap is one of the things only play-testing will settle.

If you like a duel where a move has weight, Sunmeld is the card to look at on [play.ipe.rest](https://play.ipe.rest). It is in development and has no release date.

```
ipe(); // a move should mean something
```
