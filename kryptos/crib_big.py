"""A much larger crib corpus. Justified by §A0: at 144-153 letters, ranking searches over 30k
candidates are below their own noise floor, but the crib x key-structure consistency test has a
false-positive rate near 1e-16 and is fully powered at ANY length. So the binding constraint on
PK8/PK9 is no longer compute -- it is whether the true opening is in the corpus. Enrich the corpus.

Voice, taken from the seven solved plaintexts: a first-person archivist's diary. Four of seven open
with an elapsed-time marker. PK7 ends "...I HAVE MADE PEACE WITH IT AND WILL GO HOME SOON", so PK8
opens the next chapter -- the return, or the next stage of the search.
"""
NUM = ['ONE','TWO','THREE','FOUR','FIVE','SIX','SEVEN','EIGHT','NINE','TEN','ELEVEN','TWELVE',
       'THIRTEEN','FOURTEEN','FIFTEEN','SIXTEEN','SEVENTEEN','EIGHTEEN','NINETEEN','TWENTY',
       'TWENTYONE','TWENTYTWO','TWENTYTHREE','TWENTYFOUR','TWENTYFIVE','TWENTYSIX','TWENTYSEVEN',
       'TWENTYEIGHT','TWENTYNINE','THIRTY','THIRTYONE','FORTY','FIFTY','SIXTY','SEVENTY','EIGHTY',
       'NINETY','AHUNDRED','ONEHUNDRED','ATHOUSAND','AFEW','SEVERAL','MANY','COUNTLESS']
ORD = ['FIRST','SECOND','THIRD','FOURTH','FIFTH','SIXTH','SEVENTH','EIGHTH','NINTH','TENTH',
       'ELEVENTH','TWELFTH','THIRTEENTH','FOURTEENTH','FIFTEENTH','SIXTEENTH','SEVENTEENTH',
       'EIGHTEENTH','NINETEENTH','TWENTIETH','LAST','FINAL']
UNIT = ['DAY','DAYS','WEEK','WEEKS','MONTH','MONTHS','YEAR','YEARS','WINTER','WINTERS','SUMMER',
        'SUMMERS','SPRING','SPRINGS','AUTUMN','MORNING','MORNINGS','NIGHT','NIGHTS','HOUR','HOURS',
        'SEASON','SEASONS','DECADE','DECADES']
TAIL = ['IN','INTO','INTHE','LATER','AFTER','SINCE','HAVEPASSED','PASSED','HAVEGONE','GONE',
        'ONTHEROAD','ATTHEBENCH','ATTHEFORGE','INTHEBARN','INTHEWORKSHOP','INTHEARCHIVE',
        'HOMEAGAIN','ATHOME','WITHTHEWHITESMITH','UNDERHIM','OFWORK','OFSILENCE','OFWAITING',
        'OFTHEAPPRENTICESHIP','AFTERIRETURNED','AFTERILEFT','BEFOREIRETURNED','SINCEILEFT',
        'SINCEIRETURNED','ANDIAMHOME','ANDIHAVERETURNED','ANDSTILLNOWORD','ANDNOTHING',
        'IWROTETO','IRETURNEDTO','ITOOKTHENEEDLE','IBEGANAGAIN','THEWHITESMITHDIED']
SUBJ = ['I','IHAVE','IHAD','WEHAVE','THENEEDLE','THEWHITESMITH','THEARCHIVE','THEKNOT','THETHREAD',
        'THEINNERDOOR','THEWORKSHOP','THELOG','THEACCESSIONLOG','MYHANDS','MYMASTER','PELLEGRIN']
VERB = ['RETURNEDTO','CAMEBACKTO','WENTHOMETO','LEFT','FOUND','LOSTTHE','CARRIEDTHE','PLACEDTHE',
        'UNRAVELEDTHE','OPENEDTHE','CLOSEDTHE','BEGANTO','FINISHEDTHE','WROTETO','SEARCHEDFOR',
        'ISBURIEDIN','ISHIDDENIN','LIESIN','WAITSIN','ISGONE','ISDEAD','ISMINE','ISCOMPLETE']
OBJ = ['THEARCHIVE','THELOSTARCHIVE','THEARCHIVEOFPELLEGRIN','THEWORKSHOP','THEBARN','THEGATES',
       'THENEEDLE','THEKNOT','THETHREAD','THEINNERDOOR','THEWHITESMITH','THEROADHOME','HOME',
       'THEMOUNTAIN','THEVALLEY','THELETTERS','THEMARGINALIA','THEACCESSIONLOG','MYOWNMAKING']
LIT = ['INVESTIGATIONLOGITEM','INVESTIGATIONLOGITEMNUMBER','ACCESSIONLOGITEM','THISISTHELASTENTRY',
       'THISISMYLASTENTRY','THISISTHEFINALENTRYINTHELOG','IAMTHETHIRTEENTHARCHIVIST',
       'THIRTEENPRIORARCHIVISTS','TWELVEPRIORARCHIVISTSTRIED','IHAVEMADEPEACEWITHIT',
       'THEROUTETOTHELOSTARCHIVE','ONCEUNRAVELEDITREVEALS','THETHREADINSCRIBEDWITHLETTERS',
       'IHAVEUNRAVELEDTHEKNOT','THEKNOTISUNRAVELEDATLAST','BEHINDTHEINNERDOORTHEREIS',
       'THEWHITESMITHISDEADANDI','WHENIRETURNEDTOTHEARCHIVE','ITOOKTHENEEDLEANDWENTHOME',
       'IPLACEDTHENEEDLEINTHECASE','MYHANDSAREMYOWNAGAIN','IAMNOLONGERANAPPRENTICE',
       'IHAVECOMEHOMETOTHEARCHIVE','THENEEDLEISINMYPOSSESSION','IHAVEFOUNDTHELOSTARCHIVE']

def build(minL=18, maxL=64):
    C = set()
    for n in NUM:
        for u in UNIT:
            for t in TAIL:
                s = n+u+t
                if minL <= len(s) <= maxL: C.add(s)
    for o in ORD:
        for u in ['MONTH','YEAR','WEEK','DAY','WINTER','SUMMER','MONTHI','YEARI','DAYI','ENTRY',
                  'MONTHIWROTE','YEARINTHEARCHIVE']:
            for t in TAIL[:24]:
                s = o+u+t
                if minL <= len(s) <= maxL: C.add(s)
    for s0 in SUBJ:
        for v in VERB:
            for o in OBJ:
                s = s0+v+o
                if minL <= len(s) <= maxL: C.add(s)
    for l in LIT:
        for n in ['']+NUM+ORD:
            s = l+n
            if minL <= len(s) <= maxL: C.add(s)
    for n in NUM+ORD:
        for l in ['YEARSLATERIRETURNED','YEARSAFTERILEFT','MONTHSAFTERIRETURNED',
                  'DAYSAFTERTHEINNERDOOR','WEEKSAFTERTHEWHITESMITH']:
            s = n+l
            if minL <= len(s) <= maxL: C.add(s)
    return sorted(C)

if __name__ == '__main__':
    c = build()
    from collections import Counter
    print(f"corpus {len(c):,}; lengths {dict(sorted(Counter(len(x) for x in c).items())[:8])}")
    print("samples:", c[:3], c[len(c)//3:len(c)//3+3], c[-3:])
    open('cribs_big.txt','w').write('\n'.join(c))
