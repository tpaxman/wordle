"""
WORDLE SIMULATOR

This is a script for simulating a wordle solution based on an answer and initial guess and can be run from the command line as follows:

`python wordle.py <answer> -g <guess>`
"""

import requests
import argparse
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
    parser = argparse.ArgumentParser(description='get Wordle answer and guess from command line')
    parser.add_argument('answer', metavar='a', type=str.lower, help='answer to the Wordle puzzle (5 letter word)')
    parser.add_argument('-g', '--guess', metavar='g', type=str.lower, default=None, help='initial guess to the puzzle')
    args = parser.parse_args()

    # extract command line arguments
    answer = args.answer
    guess = args.guess

    wordlength = len(answer)

    # import word lists
    scrabblewords = download_wordlist(WORDLIST_URL_SCRABBLE, wordlength)
    mostcommon_ordered = download_wordlist(WORDLIST_URL_COMMON, wordlength)

    # simulate a recursive wordle solutions
    simulate = partial(simulate_wordle, answer=answer, words=scrabblewords, guess=guess)

    print('\nusing character position likelihood:')
    simulate(rankwords=order_by_charposition_likelihood)

    print('\nusing word usage frequency:')
    simulate(rankwords=partial(order_by_usage_frequency, mostcommon_ordered=mostcommon_ordered))
             


def download_wordlist(url: str, wordlen: int) -> list:
    """download words from raw text file at url"""
    rawtext = requests.get(url).text
    wordlist = [w.lower().strip() for w in rawtext.split('\n') if len(w)==wordlen]
    return wordlist


def simulate_wordle(answer: str, words: set, rankwords: Callable, guess: str=None, guessnum: int=1) -> dict:
    """run a recursive simulation using a function to choose each successive guess"""
    guess = guess if guess else rankwords(words)[0]
    result = get_result(guess, answer)
    words = rankwords(get_possible_words(words, guess, result))
    print(guessnum, guess, len(words), ', '.join(words[:15]))
    guessnum = guessnum + 1
    guess = words[0]
    if guess == answer:
        print(guessnum, guess)
    else:
        simulate_wordle(answer=answer, words=words, rankwords=rankwords, guess=guess, guessnum=guessnum)


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
    # first pass: assign green and grey where possible; leave ambiguous cases as "_"
    firstpass = ["GREEN" if g == a else "GREY" if g not in answer else "_"
                   for g, a in zip(guess, answer)]

    # use first pass to match with possible result candidate from the set of all permutations
    result_permutations = set(product(MARKS, repeat=len(guess)))
    candidate_results = {m for m in result_permutations
        if {('GREEN','GREEN'),('GREY','GREY'),('_','GREY'),('_','YELLOW')}.issuperset(zip(firstpass, m))
    }

    # finally: filter candidate results to those that are consistent with the final answer
    ok_results = [result for result in candidate_results if answer in get_possible_words({answer}, guess, result)]

    # since there can occasionally be more than one valid result, just use the first
    return ok_results[0] # there can sometimes be more than one possible result


def order_by_charposition_likelihood(words: set) -> list:
    """
    order a set of words by highest "position likelihood score", i.e. where the frequencies
    of each character at each position are calculated based on the total set of possible
    words and are summed to give a score measure.
    """
    # get a dict of letter instance fractions at each position
    wordlength = get_wordlength_from_set(words)
    charposition_likelihoods = {
        (pos, char): [w[pos] for w in words].count(char) / len(words)
        for pos in range(wordlength) for char in CHARS
    }
    # assume that the word with the highest sum of positional frequencies is best
    word_scores = {
        w: sum(charposition_likelihoods.get(k,0) for k in enumerate(w))
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
    assert len(set(map(get_wordlength_from_set, [words, mostcommon_ordered]))), "all words must have same length"
    mostcommonranks = {word: rank for rank, word in enumerate(mostcommon_ordered)}
    return sorted(words, key=lambda x: mostcommonranks.get(x, 1e11))


def get_wordlength_from_set(words: set) -> int:
    unique_wordlengths = list(set(map(len, words)))
    assert len(unique_wordlengths)==1, "all words must have the same length"
    wordlength = unique_wordlengths[0]
    return wordlength


if __name__=='__main__':
    main()
