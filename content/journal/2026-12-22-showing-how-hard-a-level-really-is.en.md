---
slug: 2026-12-22-showing-how-hard-a-level-really-is
lang: en
title: "Showing how hard a level really is"
alt_title: "난이도를 솔직하게 보여 주기"
description: "How Inkisle measures level difficulty with bots, and why that is not the same as human players. What the numbers can tell you and what they cannot."
excerpt: "We test Inkisle levels with simulated players. It is useful, and it has limits, which is why we say so."
copy_review: iris 2026-11-15
published_at: 2026-12-22T12:08+09:00
category: games
original: en
author: ipe()
keywords: Inkisle, level difficulty, game balancing, bot simulation, difficulty curve, ipe() games
---

When a level is hard, you should be able to tell whether it is meant to be. Behind Inkisle's levels there is a way of measuring difficulty, and it is worth being clear about what it does and does not show.

## How we measure

We do not have thousands of players yet, so we use simulated ones. A set of bots with different play styles, some quick and greedy, some careful, plays each level many times with different random seeds. A level's difficulty is read from how often the bots win, and a slow, error-prone bot sets a floor for what a first-time player might manage. We use the results to adjust the levels and to check that the difficulty rises smoothly rather than in jumps.

## What it tells us

It catches the plain mistakes. A level that no bot can ever beat, or one every bot clears at once, shows up quickly. It also tells us whether a level feels harder than the ones before it, which is the thing a curve is for.

## What it cannot tell us

A bot is not a person. It does not hesitate, misread the board or tap the wrong island, and its reactions are faster than yours. So a bot's win rate is not the share of people who will win. A level that looks fair in the numbers can still feel unfair in a hand, and the other way round.

Because of that, we treat the numbers as a first filter, not a verdict. Real difficulty has to be confirmed with real players, and we have not done that yet.

## Where it stands

Inkisle is marked "in development" on [play.ipe.rest](https://play.ipe.rest) and is not released. When there are real players, we will say what they found.

```
ipe(); // a number is a guess until someone plays
```
