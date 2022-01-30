import sys
from collections import Counter
from functools import partial
from itertools import product
import requests
from typing import Callable
import pandas as pd

# todo: score words based on how common they are
# todo: score words based on a guess that cuts the remaining number in half
# todo: make function to get probability that a character is in a word, given a set of words

# CONSTANTS
WORD_LENGTH = 5
WORDLIST_URL_SCRABBLE = "https://raw.githubusercontent.com/raun/Scrabble/master/words.txt"
WORDLIST_URL_ORDERED_BY_USAGE = "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-usa-no-swears-medium.txt"
CHARS_SET = set("abcdefghijklmnopqrstuvwxyz")
NUMCHARS_SET = set(range(WORD_LENGTH+1))
RESULTS_SET = set("GYN")

# SOURCE DATA
def main():
    guess, answer = sys.argv[1:]
    scrabblewords = download_scrabble_words()
    usageranks = download_common_ordered_words()

def get_possible_char_count_sets(guess: str, mark: str) -> dict:

    def possible_char_counts(char: str, guess: str, mark: str) -> set:
        charmarks = Counter(m for c,m in zip(guess, mark) if c == char)
        n_confirmed = charmarks['Y'] + charmarks['G']
        n_denied = charmarks['N']
        char_counts = NUMCHARS_SET.difference(range(n_confirmed)) if n_denied==0 else {n_confirmed}
        return char_counts

    return {char: possible_char_counts(char, guess, mark) for char in guess}


def get_possible_position_char_sets(guess: str, mark: str) -> dict:

    def possible_position_chars(position: int, guess: str, mark: str) -> set:
        g = guess[position]
        m = mark[position]
        poss_chars = {g} if m == 'G' else CHARS_SET - {g}
        return poss_chars

    return {position: possible_position_chars(position, guess, mark) for position in NUMCHARS_SET}


def mark_guess(guess: str, answer: str) -> str:
    """returns a mark for a wordle guess where G = green, Y = yellow, N = grey"""
    prelim = ''.join("G" if g == a else "N" if g not in answer else "_" for g, a in zip(guess, answer))
    markcombos = {''.join(x) for x in product(*["GYN"]*5)} 
    possible = {actual for actual in markcombos if {'GG','NN', '_N', '_Y'} >= {*map(''.join, zip(prelim, actual))})    

    def is_mark_possible(mark, guess, answer):
        charcounts = get_possible_char_count_sets(guess, mark)
        positionchars = get_possible_position_char_sets(guess, mark)
        has_expected_char_counts = all(count in charcounts.get(char, CHARS_SET) for char, count in Counter(answer))
        has_expected_position_chars = all(char in positionchars.get(position) for position, char in enumerate(answer))
        return has_expected_char_counts and has_expected_position_chars
            
    only_options = [mark for mark in mark_combos_possible if is_mark_possible(mark)]
    assert len(only_options) in (1,2), f"there are {len(only_options)} marks and I don't know why:"+"\n".join(only_options)
    selected_mark = list(only_options)[0]
    return selected_mark


def main2():

    guess, answer = sys.argv[1:]

    scrabblewords = download_scrabble_words()
    usageranks = download_common_ordered_words()
    wordlesim = partial(simulate_wordle, words=download_scrabble_words())

    # simulate with character position frequencies
    positionfreqsim = partial(wordlesim, guess_selector=select_best_word_by_position_freq)

    # simulate using usage frequencies
    bestword_by_usagefreq = partial(select_best_word_by_usage_ranking, usageranks=usageranks)
    usagefreqsim = partial(wordlesim, guess_selector=bestword_by_usagefreq)

    # model_operations = {
    #     "usage frequency": {
    #         "simfunc": usagefreqsim,
    #         "orderfunc": partial(order_by_usage_ranking, usagefreqs=usagefreqs),
    #     },
    #     "position frequency": {
    #         "simfunc": positionfreqsim,
    #         "orderfunc": order_by_position_frequency
    #     }
    # }

    # modelresults = {modelname: modelfuncs["simfunc"](guess, answer) for modelname, modelfuncs in model_operations.items()}

    # {
    # def displayresults(modelname, modelresult):
    #     print(f"\n\nmodel: {modelname}\n")
    #     for i, (guess, mark, words) in enumerate(modelresult, 1):
    #         numwords = len(words)
    #         firstfew = ', '.join(order_by_position_frequency(words)[:words_to_show]) + ' ... '*(words_to_show < numwords)
    #         print(f'{i}: "{guess}" -> {numwords: >4} remain: {firstfew}')
    #     
    # for modelname, modelresult in modelresults.items():
    #     displayresults(modelname, modelresult)
   
    model_operations = {
        "usage frequency": usagefreqsim,
        "position frequency": positionfreqsim,
    }
    words_to_show = 15
    for modelname, modelfunc in model_operations.items():
        simresult = modelfunc(guess, answer)
        print(f"\n\nmodel: {modelname}\n")
        for i, (guess, mark, words) in enumerate(simresult, 1):
            numwords = len(words)
            firstfew = ', '.join(order_by_position_frequency(words)[:words_to_show]) + ' ... '*(words_to_show < numwords)
            print(f'{i}: "{guess}" -> {numwords: >4} remain: {firstfew}')
        

    

# GET SOURCE DATA
def download_wordlist(url: str, wordlen: int) -> list:
    response = requests.get(url)
    rawtext = response.text
    lowertext = rawtext.lower()
    wordlist = [x.strip() for x in lowertext.split('\n') if len(x)==wordlen]
    return wordlist

def download_scrabble_words() -> list:
    return download_wordlist(WORDLIST_URL_SCRABBLE, WORD_LENGTH)

def download_common_ordered_words() -> dict:
    ordered_words = download_wordlist(WORDLIST_URL_ORDERED_BY_USAGE, WORD_LENGTH)
    usageranks = {word: rank for rank, word in enumerate(ordered_words, 1)}
    return usageranks


# USAGE FREQUENCY FUNCTIONS
def order_by_usage_ranking(words: set, usageranks: dict) -> list:
    return sorted(words, key=lambda x: usageranks.get(x, 1e11))

def select_best_word_by_usage_ranking(words: set, usageranks: dict) -> str:
    ordered_words = order_by_usage_ranking(words, usageranks)
    bestword = ordered_words[0]
    return bestword


# POSITION FREQUENCY FUNCTIONS

def order_by_position_frequency(words: set) -> list:
    if words:
        positionfreqs = determine_position_frequencies(words)
        scores = {w: calc_position_freq_score(w, positionfreqs) for w in words}
        return sorted(words, key=lambda x: scores.get(x, 1e11), reverse=True)
    else:
        return list(words)
    

def calc_position_freq_score(word: str, positionfreqs: dict) -> float:
    """ gets the sum of positional frequencies for each character in a word """

    assert all(len(k)==2 and isinstance(v, float) for k, v in positionfreqs.items()), (
    "positionfreqs must be a dict where the keys are pairs of (position, character)")

    keyed_word = tuple(enumerate(word))
    freq_score = sum(positionfreqs.get(k,0) for k in keyed_word)
    return freq_score

def select_best_word_by_position_freq(words: set) -> str:
    positionfreqs = determine_position_frequencies(words)
    scores = {x: calc_position_freq_score(x, positionfreqs) for x in words}
    bestword = max(scores, key=scores.get)
    return bestword

def determine_position_frequencies(words: set) -> dict:
    """
    calculates frequencies of each character in each position from the set of words given
    returns dict where keys are pairs of (position, character)
    i.e. position 0-4 and characters a-z
    e.g. {(0,'a'): 0.14, (1,'a'): 0.22, ..., (4,'z'): 0.001}
    """
    wordlengths = list(len(x) for x in words)
    assert len(set(wordlengths))==1, "all words must be same length"
    wordlength = wordlengths[0]
    numwords = len(words)
    
    positioncounts = [Counter(w[pos] for w in words) for pos in range(wordlength)]
    positionfreqs = {(pos, char): count/numwords
                     for pos, counter in enumerate(positioncounts)
                     for char, count in counter.items()}
    return positionfreqs

# GENERAL WORDLE FUNCTIONS
def simulate_wordle(guess: str, answer: str, words: set, guess_selector: Callable) -> dict:
    results = {}
    datalist = []
    while guess:
        mark = mark_guess(guess, answer)
        results = {**results, **{guess: mark}}
        words = get_allowed_words(words, results) - {guess}
        datalist.append((guess, mark, words))
        guess = guess_selector(words) if words else None
    return datalist


def mark_guess(guess: str, answer: str) -> str:
    """returns a mark for a wordle guess where G = green, Y = yellow, N = grey"""
    # define easy ones (G and N) and leave _ for things that could be Y or N
    prelim_mark = ''.join('G' if g==a else ('N' if g not in answer else '_') for g, a in zip(guess, answer))
    # make a set of all possible marks
    marks = {''.join(x) for x in product(*["GYN"]*5)} 
    # filter set of all marks to only be ones that match up with the preliminary mark by looking at each position
    prefilt_marks = {mm for mm in marks if all((p=='_' and m!='G') or p==m for p, m in zip(prelim_mark, mm))}
    # now filter the set of marks again knowing the count of G and Y in the mark that need to be in the mark for each character
    Cg = Counter(guess)
    Ca = Counter(answer)
    overlaps = set(guess) & set(answer)
    only_options = [mark for mark in prefilt_marks if all(min(Cg[char],Ca[char])==sum(n for c,n in Counter(mm for cc, mm in zip(guess,mark) if cc==char).items() if c in 'YG') for char in overlaps)]
    # some cases there are two correct marks for example if the answer has 2 w's and the guess has 3 w's 
    assert len(only_options) in (1,2), f"there are {len(only_options)} marks and I don't know why:"+"\n".join(only_options)
    # keep the first mark (usually should only be one and all should be correct anyway)
    selected_mark = list(only_options)[0]
    return selected_mark


def get_allowed_words(words: list, guess_results: dict) -> set:
    """
    gets a set of all allowed words (i.e. potential candidates)
    based on previous wordle guess results.
    """
    assert all(CHARS_SET.issuperset(word) and RESULTS_SET.issuperset(mark) and len(word)==len(mark)
               for word, mark in guess_results.items())

    def tabulate_guess_results_dict(guess_results: dict):
    
        def tabulate_guess_result(guessword, result):
            guessword = guessword.lower()
            result = result.upper()
            assert (len(guessword) == WORD_LENGTH and
                    len(result) == WORD_LENGTH and
                    set(result).issubset(RESULTS_SET))
            return pd.DataFrame(zip(guessword, result), columns=['char', 'mark']).rename_axis('pos').reset_index()
    
        tables = [tabulate_guess_result(*x) for x in guess_results.items()]
        index = guess_results.keys()
        return pd.concat(tables, keys=index).droplevel(-1).rename_axis('guess').reset_index()
 
    def generate_get_info_sets(df_results: pd.DataFrame):
        def get_info_sets(idxcols, aggcol, applyfun, fullset):
            
            def assign_apply(df, colname, row_function):
                return df.assign(**{colname: df.apply(row_function, axis=1)})
            

            return (df_results[idxcols]
                    .value_counts()
                    .unstack()
                    .reindex(list(RESULTS_SET), axis=1)
                    .fillna(0)
                    .astype(int)
                    .reset_index()
                    .pipe(assign_apply, aggcol, applyfun)
                    .groupby(idxcols[0])
                    .agg({aggcol: lambda x: fullset.intersection(*x.to_list())})
                    [aggcol]
                    .to_dict())
        return get_info_sets 

    def word_allowed(w, charcounts, position_chars):
        check1 = all(Counter(w)[c] in n for c, n in charcounts.items())
        check2 = all(w[pos] in ok for pos, ok in position_chars.items())
        return all([check1, check2]) 

    def calc_possible_counts(G, Y, N):
        n_min = sum((G,Y))
        return NUMCHARS_SET.difference(range(n_min)) if (N==0) else {n_min}
 
    def calc_allowed_chars(char,G,Y,N):
        if G>0:
            return {char}
        elif sum([Y,N])>0:
            return CHARS_SET - {char}
        else:
            return CHARS_SET
 
    df_results = tabulate_guess_results_dict(guess_results)

    get_info_sets = generate_get_info_sets(df_results)

    charcounts = get_info_sets(
        idxcols=['char', 'guess', 'mark'],
        aggcol='numchars',
        applyfun=lambda r: calc_possible_counts(r.G, r.Y, r.N),
        fullset=NUMCHARS_SET
    )

    position_chars = get_info_sets(
        idxcols=['pos', 'char', 'mark'],
        aggcol='okchars',
        applyfun=lambda r: calc_allowed_chars(r.char, r.G, r.Y, r.N),
        fullset=CHARS_SET
    )
    
    allowed_words = {w for w in words if word_allowed(w, charcounts, position_chars)}
    return allowed_words


if __name__ == '__main__':
    main()
