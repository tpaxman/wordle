# WORDLE SIMULATOR

This is a script for simulating a Wordle solution based on an answer and an (optional) initial guess.
It can be run from the command line as follows:


```
python wordle.py <answer> -g <guess>
```

## Terminology:

- "answer": the five-letter answer to the Wordle puzzle (i.e. target word)
- "guess": a five-letter word that is submitted as a guess at the answer
- "result": the colors assigned to a guessed word giving info about each letter (GREEN, YELLOW, or GREY) 


## Process Steps:

- The script requires the 'answer' and optionally takes an initial 'guess' in input arguments.
- If no initial guess is provided, default values are obtained via the 'next guess' models described below.
- The guess is checked against the answer to generate a 'result' consisting of a
5 element combination of any of the following colors:
    - "GREEN" for a character in the correct position
    - "YELLOW" for a character in the word but not at that position
    - "GREY" for a character not in the word
- A set of all five-letter words is filtered down to a subset of possible answers based
on the result of the guess. (The words are taken from the Scrabble dictionary)
- This set of possible words is then ordered by rank based on either of the following criteria:

    1. Highest "positional likelihood score" which is a measure of how common each character is at each position
    within the set of possible words

    2. Most commonly used based on an analysis of n-grams

- The first item in the "ranked" list is chosen as the next guess and the process repeats until the actual
answer is guessed.

- The output at each step consists of the guess, the number of resulting possible words
and a preview of the ranked list of words. This is shown for each of the two ranking methods
described above.
