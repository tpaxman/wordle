import sys
import requests
from collections import Counter
from functools import partial
from itertools import product
from typing import Callable

# CONSTANTS
WORDLEN = 5
WORDLIST_URL_SCRABBLE = "https://raw.githubusercontent.com/raun/Scrabble/master/words.txt"
WORDLIST_URL_ORDERED_BY_USAGE = "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-usa-no-swears-medium.txt"
CHARS = "abcdefghijklmnopqrstuvwxyz"
MARKS = {"GREEN", "YELLOW", "GREY"}

def main():
    guess, answer = sys.argv[1:]
    assert set(map(len, (guess, answer))) == {WORDLEN}, "guess and answer must be five-letter words"
    wordle_sim_scrabble = partial(simulate_wordle, words=download_scrabble_words())
    print('\nusing character position likelihood:')
    wordle_sim_scrabble(guess, answer, guess_ranker=order_by_position_likelihood)
    print('\nusing word usage frequency:')
    wordle_sim_scrabble(guess, answer, guess_ranker=partial(order_by_usage_frequency, frequencies=download_common_ordered_words()))


def calc_charcount_constraints(guess: str, mark: str) -> dict:

    instances_guessed = Counter(guess)   
    instances_confirmed = Counter(g for g, m in zip(guess, mark) if m != "GREY")
    
    def get_allowed_charcounts(char: str) -> set:
        n_guessed = instances_guessed[char]
        n_confirmed = instances_confirmed[char]
        n_maxpossible = n_confirmed if n_guessed > n_confirmed else len(guess)
        return set(range(n_confirmed, n_maxpossible+1))

    return {char: get_allowed_charcounts(char) for char in set(guess)}


def calc_position_constraints(guess: str, mark: str) -> dict:

    def possible_position_chars(position: int) -> set:
        set_operation = 'intersection' if mark[position]=="GREEN" else 'difference'
        set_method = getattr(set(CHARS), set_operation)
        return set_method(guess[position])

    return {position: possible_position_chars(position)
            for position in range(len(guess))}


def is_word_allowed(word: str, charcount_constraints: dict, position_constraints: dict) -> bool:
    instances = Counter(word)
    return all((
        all(instances[c] in n for c, n in charcount_constraints.items()),
        all(word[p] in c for p, c in position_constraints.items())
    ))


def get_allowed_words(words: set, guess: str, mark: str) -> set:
    charcount_constraints = calc_charcount_constraints(guess, mark)
    position_constraints = calc_position_constraints(guess, mark)
    return [word for word in words if is_word_allowed(word, charcount_constraints, position_constraints)]


def get_mark(guess: str, answer: str) -> str:
    """returns a mark for a wordle guess where G = green, Y = yellow, N = grey"""
    partialmark = ["GREEN" if g == a else "GREY" if g not in answer else "_"
                   for g, a in zip(guess, answer)]
    mark_permutations = set(product(MARKS, repeat=5))
    candidate_marks = {m for m in mark_permutations
        if {('GREEN','GREEN'),('GREY','GREY'),('_','GREY'),('_','YELLOW')}.issuperset(zip(partialmark, m))
    }
    ok_marks = [mark for mark in candidate_marks if answer in get_allowed_words({answer}, guess, mark)]
    return ok_marks[0] # there can sometimes be more than one possible mark


def order_by_position_likelihood(words: set) -> list:
    position_likelihoods = {
        (pos, char): [w[pos] for w in words].count(char) / len(words)
        for pos in range(WORDLEN) for char in CHARS
    }
    word_scores = {
        w: sum(position_likelihoods.get(k,0) for k in enumerate(w))
        for w in words
    }
    ordered_words = sorted(words, key=word_scores.get, reverse=True)
    return ordered_words


def order_by_usage_frequency(words: set, frequencies: dict) -> list:
    return sorted(words, key=lambda x: frequencies.get(x, 1e11))


def simulate_wordle(guess: str, answer: str, words: set, guess_ranker: Callable, guessnum: int=1) -> dict:
    mark = get_mark(guess, answer)
    allowed_words = get_allowed_words(words, guess, mark)
    ranked_words = guess_ranker(allowed_words)
    next_guess = ranked_words[0]
    print(guessnum, guess, len(ranked_words), ranked_words[:10])
    if next_guess == answer:
        print(guessnum+1, next_guess)
    else:
        return simulate_wordle(next_guess, answer, ranked_words, guess_ranker, guessnum+1)


def download_wordlist(url: str, wordlen: int) -> list:
    response = requests.get(url)
    rawtext = response.text
    lowertext = rawtext.lower()
    wordlist = [x.strip() for x in lowertext.split('\n') if len(x)==wordlen]
    return wordlist


def download_scrabble_words() -> list:
    return download_wordlist(WORDLIST_URL_SCRABBLE, WORDLEN)


def download_common_ordered_words() -> dict:
    ordered_words = download_wordlist(WORDLIST_URL_ORDERED_BY_USAGE, WORDLEN)
    usageranks = {word: rank for rank, word in enumerate(ordered_words, 1)}
    return usageranks


if __name__=='__main__':
    main()
