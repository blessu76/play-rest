---
slug: 2026-11-26-looking-two-moves-ahead
lang: en
title: "Looking two moves ahead"
alt_title: "두 수 앞을 보는 법"
description: "You do not need to calculate deeply to play well. A simple habit of checking your move, the reply and your answer catches most mistakes in a short round."
excerpt: "A plain look-ahead habit for turn-based games: three questions, no notebook, thirty seconds."
published_at: 2026-11-26T12:33+09:00
category: games
original: en
author: ipe()
keywords: look ahead, planning moves, strategy tips, turn-based games, beginner tips, thinking in games, ipe() games
---

Strong players are often described as seeing many moves ahead. That is true for some positions, and it is also a poor guide for the rest of us. You do not need ten moves of depth. Two is enough to catch most of the mistakes that matter in a short round.

## The habit

Before you commit to a move, run three small questions.

What do I want this move to do? Say it in a few words. If you cannot, you may be moving only because it is your turn.

How might they answer? Pick the reply that would hurt most, not the one you would like. Most mistakes come from imagining the opponent's kindest answer.

What would I do next? If your plan survives that reply and you still have a good move, go ahead. If you would be stuck, look for another move.

That is the whole technique: your move, their reply, your answer. It takes a few seconds once you get used to it.

## Why two is enough

The first reply is where most surprises live. Past that point the possibilities spread out and the guesses get weaker. A shallow, honest look at the worst reply gives you more than a deep, hopeful one.

It also keeps your thinking short. In a break you might have a minute. A habit that fits is better than a method that does not.

## When hidden information gets in the way

If part of the board is hidden, you cannot see the reply you should fear. In [Iltonggi](https://iltonggi.ipe.rest), fog and spies mean you sometimes guess. Then the habit changes slightly: ask what the worst reasonable reply would be and whether you could survive it. You do not need to know exactly what is there to prepare for what might be.

## When the opponent is an AI

Against an AI, the same questions apply, with one extra. In [Sunmeld](https://sunmeld.ipe.rest), every opponent has its own habits. After a few rounds, add a fourth question: what does this opponent usually do? You are no longer imagining a generic reply, you are remembering a specific one.

Neither game is released. Iltonggi is "coming soon" and Sunmeld is in development.

```
ipe(); // move, reply, answer
```
