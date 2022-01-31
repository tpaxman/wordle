"""
WORDLE SIMULATOR

This is a script for simulating a wordle solution based on an answer and initial guess.
It can be run from the command line as follows:

`python wordle.py <answer> <guess>`


Terminology:

- "answer": the five-letter answer to the wordle puzzle (i.e. target word)
- "guess": a five-letter word that is submitted as a guess at the answer
- "result": the colors assigned to a guessed word giving info about each letter (GREEN, YELLOW, or GREY) 


Process:

- The script requires the 'answer' and initial 'guess' in input arguments.
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
"""

import sys
import requests
from collections import Counter
from functools import partial
from itertools import product
from typing import Callable

WORDLIST_URL_SCRABBLE = "https://raw.githubusercontent.com/raun/Scrabble/master/words.txt"
WORDLIST_URL_COMMON = "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-usa-no-swears.txt"
CHARS = "abcdefghijklmnopqrstuvwxyz"
MARKS = {"GREEN", "YELLOW", "GREY"}


def main():

    # Read answer and guess inputs from command line
    answer, guess = (x.lower() for x in sys.argv[1:])
    wordlength = len(answer)
    assert len(guess) == wordlength, "guess and answer must both be the same length"

    # import word lists
    scrabblewords = download_wordlist(WORDLIST_URL_SCRABBLE, wordlength)
    mostcommon_ordered = download_wordlist(WORDLIST_URL_COMMON, wordlength)

    # simulate a recursive wordle solutions
    print('\nusing character position likelihood:')
    simulate_wordle(guess, answer, scrabblewords, order_by_position_likelihood)
    print('\nusing word usage frequency:')
    simulate_wordle(guess, answer, scrabblewords, partial(order_by_usage_frequency, mostcommon_ordered=mostcommon_ordered))


def download_wordlist(url: str, wordlen: int) -> list:
    """download words from raw text file at url"""
    rawtext = requests.get(url).text
    wordlist = [w.lower().strip() for w in rawtext.split('\n') if len(w)==wordlen]
    return wordlist


def simulate_wordle(guess: str, answer: str, words: set, rankwords: Callable, guessnum: int=1) -> dict:
    """run a recursive simulation using a function to choose each successive guess"""
    result = get_result(guess, answer)
    words = rankwords(get_possible_words(words, guess, result))
    print(guessnum, guess, len(words), ', '.join(words[:15]))
    guessnum = guessnum + 1
    guess = words[0]
    if guess == answer:
        print(guessnum, guess)
    else:
        simulate_wordle(guess, answer, words, rankwords, guessnum)


def get_possible_words(words: set, guess: str, result: list) -> set:
    """get set of possible words based on an initial set of words, a wordle guess, and its result"""
    charcount_constraints = calc_charcount_constraints(guess, result)
    position_constraints = calc_position_constraints(guess, result)
    return [w for w in words if is_word_possible(w, charcount_constraints, position_constraints)]


def calc_charcount_constraints(guess: str, result: list) -> dict:
    """
    get a dict of possible numbers of characters in the word based on the guess and result
    e.g. the result {"a": {2,3,4,5}, "d": {1}, "n": {0}} 
    means only words containing between 2 and 5 "a", 1 "d" and no "n" characters are possible
    """
    instances_guessed = Counter(guess)   
    instances_confirmed = Counter(g for g, m in zip(guess, result) if m != "GREY")
    
    def get_possible_charcounts(char: str) -> set:
        """get set of all possible numbers of letters in the word"""
        n_guessed = instances_guessed[char]
        n_confirmed = instances_confirmed[char]
        n_maxpossible = n_confirmed if n_guessed > n_confirmed else len(guess)
        return set(range(n_confirmed, n_maxpossible+1))

    return {char: get_possible_charcounts(char) for char in set(guess)}


def calc_position_constraints(guess: str, result: list) -> dict:
    """
    get a dict of possible characters at each position in the word based on the guess and result
    e.g. the result {0: {"a", "b", "d", "e", ..., "z"}, 1: {"a"}, 2: {"g"}, 3: {"b", "c", ...}...}
    means that the first character can be anything but "c", the second is "a", the third is "g"
    and so on.
    """
    def get_possible_positions(position: int) -> set:
        """get set of possible characters in a specified position"""
        set_operation = 'intersection' if result[position]=="GREEN" else 'difference'
        return getattr(set(CHARS), set_operation)(guess[position])

    return {position: get_possible_positions(position) for position in range(len(guess))}


def is_word_possible(word: str, charcount_constraints: dict, position_constraints: dict) -> bool:
    """
    check if word is possible based on the possible character counts and position characters
    """
    instances = Counter(word)
    return all((
        all(instances[c] in n for c, n in charcount_constraints.items()),
        all(word[p] in c for p, c in position_constraints.items())
    ))


def get_result(guess: str, answer: str) -> str:
    """
    returns a result for a wordle guess as a list of 5 colors, either 
    green, grey, or yellow to denote the result given to the guess
    e.g. a result could be ["GREEN", "GREY", "GREY", "YELLOW", "GREY"] 
    """
    partialresult = ["GREEN" if g == a else "GREY" if g not in answer else "_"
                   for g, a in zip(guess, answer)]
    result_permutations = set(product(MARKS, repeat=len(guess)))
    candidate_results = {m for m in result_permutations
        if {('GREEN','GREEN'),('GREY','GREY'),('_','GREY'),('_','YELLOW')}.issuperset(zip(partialresult, m))
    }
    ok_results = [result for result in candidate_results if answer in get_possible_words({answer}, guess, result)]
    return ok_results[0] # there can sometimes be more than one possible result


def order_by_position_likelihood(words: set) -> list:
    """
    order a set of words by highest "position likelihood score", i.e. where the frequencies
    of each character at each position are calculated based on the total set of possible
    words and are summed to give a score measure.
    """
    unique_wordlengths = list(set(map(len, words)))
    assert len(unique_wordlengths)==1, "all words must have the same length"
    wordlength = unique_wordlengths[0]
    position_likelihoods = {
        (pos, char): [w[pos] for w in words].count(char) / len(words)
        for pos in range(wordlength) for char in CHARS
    }
    word_scores = {
        w: sum(position_likelihoods.get(k,0) for k in enumerate(w))
        for w in words
    }
    ordered_words = sorted(words, key=word_scores.get, reverse=True)
    return ordered_words


def order_by_usage_frequency(words: set, mostcommon_ordered: list) -> list:
    """
    orders a set of words by most commonly used words according to a list given by
    mostcommon_ordered. If the word in the set does not occur in the list of ordered
    words, it is assigned an arbitrarily low ranking
    """
    mostcommonranks = {word: rank for rank, word in enumerate(mostcommon_ordered)}
    return sorted(words, key=lambda x: mostcommonranks.get(x, 1e11))


if __name__=='__main__':
    main()
