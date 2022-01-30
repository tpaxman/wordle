import sys
import requests
from collections import Counter
from functools import partial
from itertools import product
from typing import Callable

WORDLEN = 5
WORDLIST_URL_SCRABBLE = "https://raw.githubusercontent.com/raun/Scrabble/master/words.txt"
WORDLIST_URL_COMMON = "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-usa-no-swears-medium.txt"
CHARS = "abcdefghijklmnopqrstuvwxyz"
MARKS = {"GREEN", "YELLOW", "GREY"}


def main():
    guess, answer = sys.argv[1:]
    scrabblewords = download_wordlist(WORDLIST_URL_SCRABBLE, WORDLEN)
    mostcommon_ordered = download_wordlist(WORDLIST_URL_COMMON, WORDLEN)

    assert set(map(len, (guess, answer))) == {WORDLEN}, "guess and answer must be five-letter words"

    wordle_sim_scrabble = partial(simulate_wordle, words=scrabblewords)
    print('\nusing character position likelihood:')
    wordle_sim_scrabble(guess, answer, guess_ranker=order_by_position_likelihood)
    print('\nusing word usage frequency:')
    wordle_sim_scrabble(guess, answer, guess_ranker=partial(order_by_usage_frequency, mostcommon_ordered=mostcommon_ordered))


def download_wordlist(url: str, wordlen: int=None) -> list:
    rawtext = requests.get(url).text
    wordlist = [x.lower().strip() for x in rawtext.split('\n')]
    if wordlen:
        return [w for w in wordlist if len(w)==wordlen]
    else:
        return wordlist


def simulate_wordle(guess: str, answer: str, words: set, guess_ranker: Callable, guessnum: int=1) -> dict:
    mark = get_mark(guess, answer)
    allowed_words = get_allowed_words(words, guess, mark)
    ranked_words = guess_ranker(allowed_words)
    print(guessnum, guess, len(ranked_words), ranked_words[:10])
    guessnum = guessnum + 1
    nextguess = ranked_words[0]
    if nextguess == answer:
        print(guessnum, nextguess)
    else:
        return simulate_wordle(nextguess, answer, ranked_words, guess_ranker, guessnum)


def get_allowed_words(words: set, guess: str, mark: list) -> set:
    charcount_constraints = calc_charcount_constraints(guess, mark)
    position_constraints = calc_position_constraints(guess, mark)
    return [word for word in words if is_word_allowed(word, charcount_constraints, position_constraints)]


def calc_charcount_constraints(guess: str, mark: list) -> dict:

    instances_guessed = Counter(guess)   
    instances_confirmed = Counter(g for g, m in zip(guess, mark) if m != "GREY")
    
    def get_allowed_charcounts(char: str) -> set:
        n_guessed = instances_guessed[char]
        n_confirmed = instances_confirmed[char]
        n_maxpossible = n_confirmed if n_guessed > n_confirmed else WORDLEN
        return set(range(n_confirmed, n_maxpossible+1))

    return {char: get_allowed_charcounts(char) for char in set(guess)}


def calc_position_constraints(guess: str, mark: list) -> dict:

    def get_allowed_positions(position: int) -> set:
        set_operation = 'intersection' if mark[position]=="GREEN" else 'difference'
        return getattr(set(CHARS), set_operation)(guess[position])

    return {position: get_allowed_positions(position) for position in range(WORDLEN)}


def is_word_allowed(word: str, charcount_constraints: dict, position_constraints: dict) -> bool:
    instances = Counter(word)
    return all((
        all(instances[c] in n for c, n in charcount_constraints.items()),
        all(word[p] in c for p, c in position_constraints.items())
    ))


def get_mark(guess: str, answer: str) -> str:
    """returns a mark for a wordle guess where G = green, Y = yellow, N = grey"""
    partialmark = ["GREEN" if g == a else "GREY" if g not in answer else "_"
                   for g, a in zip(guess, answer)]
    mark_permutations = set(product(MARKS, repeat=WORDLEN))
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


def order_by_usage_frequency(words: set, mostcommon_ordered: list) -> list:
    mostcommonranks = {word: rank for rank, word in enumerate(mostcommon_ordered, 1)}
    return sorted(words, key=lambda x: mostcommonranks.get(x, 1e11))


if __name__=='__main__':
    main()
