---
slug: 2026-11-20-what-a-tempo-is-worth
lang: en
title: "What a tempo is worth"
alt_title: "한 수의 값, 템포"
description: "In a game of alternating turns, a move is also a unit of time. What 'tempo' means, why wasting it hurts, and a simple way to notice it in a short game."
excerpt: "A short guide to tempo in turn-based games: the idea that every move spent is a move the other side gets back."
published_at: 2026-11-20T12:19+09:00
category: games
original: en
author: ipe()
keywords: tempo, turn-based strategy, game tips, alternating turns, chess terms, casual strategy, ipe() games
---

In games where the players alternate, a move is more than a choice. It is also a small piece of time. Each turn you spend is a turn in which the other side is free to act, and a good deal of the skill in these games is about spending those turns well.

Chess players have a word for this: tempo, from the Italian for time. The idea is older and wider than chess.

## The idea in one line

A tempo is one move's worth of time. If you make a move that achieves something, you have used your tempo well. If you make a move that the opponent can simply undo, or that does nothing, you have spent a tempo and the other side has gained one.

"Gaining a tempo" means making a useful move that also forces the opponent to answer. They spend their turn replying, and you are one move ahead of where you started.

## Why it matters in short games

On a large board, a wasted move disappears into the noise. On a small board, or in a short round, it does not. Every turn counts for a bigger share of the whole game, and there are fewer chances to recover.

That is why a round with few turns can feel tense out of proportion to its size. If a game lasts a handful of moves for each player, then "I wasted one" can decide it.

## How to notice it

You do not need the word to use the idea. Before a move, ask two small questions.

First: does this move do something that will still be true after the opponent replies? A move that is erased by the very next reply was a tempo spent for nothing.

Second: does this move make the opponent do something? If it leaves them free to carry out their own plan, you have handed them a tempo. If it takes away their choice, you have gained one.

You will not be able to answer both every turn. Asking them, though, makes a hurried move a little less hurried.

## A note on our games

In [Sunmeld](https://sunmeld.ipe.rest) you and an AI opponent alternate dropping stones into one shared tub, and whoever places the last stone when the tub overflows loses. In a game like that, the shared space is the thing being spent, and it seems natural to ask whether a given stone gives away room. [Iltonggi](https://iltonggi.ipe.rest) is turn-based as well, with a first game of 20 turns, which is short enough that a wasted turn is noticeable.

We say this as a way of looking at these games, not as tested strategy. Neither is released: Iltonggi is marked "coming soon" and Sunmeld is in development.

```
ipe(); // spend the turn on something
```
