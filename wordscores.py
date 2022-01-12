import sys
from collections import Counter
import pandas as pd

def main():

    selectfunc, n = sys.argv[1:]
    assert selectfunc in ('nlargest', 'nsmallest')
    n = int(n)

    with open('words.txt') as f: 
        x = f.read()

    fives = [w for w in x.split('\n') if len(w)==5]
    fivesflat = ''.join(fives)
    c = Counter(fivesflat)

    charfreqs = {k: v/len(fivesflat) for k, v in c.items()}
    triples = [x for x in fives if len(set(x))==3]
    scores = pd.Series({x: sum(charfreqs.get(y) for y in x) for x in triples})

    print(selectfunc, getattr(scores, selectfunc)(n), sep='\n') 

if __name__=='__main__':
    main()
