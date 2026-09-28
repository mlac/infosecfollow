/* Gromark / running-key primer exhaustion kernel.
 *
 * Model covered (mode 0, "shift-ioc"):
 *     C[i] = MIX(P[i]) + k[i]   (mod 26)      -- mixed alphabet applied BEFORE the shift
 *   Peeling the correct k leaves MIX(P), a MONOALPHABETIC image of the plaintext, so its
 *   IoC is English regardless of the (unknown) mixed alphabet and regardless of any
 *   columnar transposition sitting underneath the substitution.
 *   Score = IoC of  (c[i] + sign*k[i]) mod 26,  c read in a given text alphabet.
 *
 * Model covered (mode 1, "class-ioc"):
 *     C[i] = MIX[(P[i] + k[i]) mod 26]        -- true ACA Gromark, MIX applied AFTER the shift
 *   Now no shift of C is monoalphabetic, but the positions sharing a key value v are:
 *   restricted to {i : k[i]=v} the cipher is monoalphabetic.  Score = pooled within-class
 *   IoC.  Alphabet- and direction-independent, but sqrt(MOD) times noisier.
 *
 * k[] is produced from an L-digit primer by one of four recurrences, modulus MOD.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define MAXT 96
#define MAXN 1024
#define MAXL 16
#define MAXK 12

typedef struct {
    char name[64];
    int mode;      /* 0 shift-ioc, 1 class-ioc */
    int sign;      /* +1 / -1, mode 0 only     */
    int n;
    unsigned char c[MAXN];
    double bestsc[MAXK];
    unsigned char bestpr[MAXK][MAXL];
    double sum, sumsq;
    long long cnt;
} Target;

static Target T[MAXT];
static int NT = 0;
static int MOD = 10, L = 7, NMAX = 504, TOPK = 8, REC = 0;
static unsigned char lut[80];

/* rec: 0 aca  k[i]=k[i-L]+k[i-L+1] | 1 lag1 k[i]=k[i-L]+k[i-1]
       2 fib  k[i]=k[i-1]+k[i-2]    | 3 subaca k[i]=k[i-L]-k[i-L+1] */
static inline void genkey(unsigned char *k)
{
    int i, t;
    switch (REC) {
    case 0: for (i = L; i < NMAX; i++) { t = k[i-L] + k[i-L+1]; if (t >= MOD) t -= MOD; k[i] = (unsigned char)t; } break;
    case 1: for (i = L; i < NMAX; i++) { t = k[i-L] + k[i-1];   if (t >= MOD) t -= MOD; k[i] = (unsigned char)t; } break;
    case 2: for (i = L; i < NMAX; i++) { t = k[i-1] + k[i-2];   if (t >= MOD) t -= MOD; k[i] = (unsigned char)t; } break;
    default:for (i = L; i < NMAX; i++) { t = k[i-L] - k[i-L+1]; if (t < 0)    t += MOD; k[i] = (unsigned char)t; } break;
    }
}

static inline void record(Target *t, double sc, const unsigned char *pr)
{
    t->sum += sc; t->sumsq += sc * sc; t->cnt++;
    if (sc <= t->bestsc[TOPK-1]) return;
    int j = TOPK - 1;
    while (j > 0 && t->bestsc[j-1] < sc) {
        t->bestsc[j] = t->bestsc[j-1];
        memcpy(t->bestpr[j], t->bestpr[j-1], L);
        j--;
    }
    t->bestsc[j] = sc;
    memcpy(t->bestpr[j], pr, L);
}

static void score_all(const unsigned char *k, const unsigned char *pr)
{
    unsigned int h[26];
    unsigned int cc[26*26];
    int ti, i, x, v;
    for (ti = 0; ti < NT; ti++) {
        Target *t = &T[ti];
        int n = t->n;
        const unsigned char *c = t->c;
        double sc;
        if (t->mode == 0) {
            memset(h, 0, sizeof(h));
            if (t->sign > 0) { for (i = 0; i < n; i++) h[lut[c[i] + k[i]]]++; }
            else             { for (i = 0; i < n; i++) h[lut[c[i] + 26 - k[i]]]++; }
            long long num = 0;
            for (x = 0; x < 26; x++) num += (long long)h[x] * (h[x] - 1);
            sc = (double)num / ((double)n * (n - 1));
        } else {
            memset(cc, 0, sizeof(unsigned int) * MOD * 26);
            for (i = 0; i < n; i++) cc[k[i] * 26 + c[i]]++;
            long long num = 0, den = 0;
            for (v = 0; v < MOD; v++) {
                unsigned int rs = 0;
                const unsigned int *row = cc + v * 26;
                for (x = 0; x < 26; x++) { num += (long long)row[x] * (row[x] - 1); rs += row[x]; }
                den += (long long)rs * (rs - 1);
            }
            sc = den ? (double)num / (double)den : 0.0;
        }
        record(t, sc, pr);
    }
}

int main(int argc, char **argv)
{
    if (argc < 2) { fprintf(stderr, "usage: gk_kernel spec\n"); return 1; }
    FILE *f = fopen(argv[1], "r");
    if (!f) { perror("spec"); return 1; }
    char tok[64];
    int enumerate = 1, nlist = 0;
    unsigned char *plist = NULL;
    while (fscanf(f, "%63s", tok) == 1) {
        if      (!strcmp(tok, "MOD"))   fscanf(f, "%d", &MOD);
        else if (!strcmp(tok, "L"))     fscanf(f, "%d", &L);
        else if (!strcmp(tok, "NMAX"))  fscanf(f, "%d", &NMAX);
        else if (!strcmp(tok, "TOPK"))  fscanf(f, "%d", &TOPK);
        else if (!strcmp(tok, "REC"))   fscanf(f, "%d", &REC);
        else if (!strcmp(tok, "ENUM"))  fscanf(f, "%d", &enumerate);
        else if (!strcmp(tok, "PRIMERS")) {
            fscanf(f, "%d", &nlist);
            plist = malloc((size_t)nlist * L);
            for (int i = 0; i < nlist; i++)
                for (int j = 0; j < L; j++) { int v; fscanf(f, "%d", &v); plist[(size_t)i*L+j] = (unsigned char)v; }
        }
        else if (!strcmp(tok, "TARGET")) {
            Target *t = &T[NT++];
            fscanf(f, "%63s %d %d %d", t->name, &t->mode, &t->sign, &t->n);
            for (int i = 0; i < t->n; i++) { int v; fscanf(f, "%d", &v); t->c[i] = (unsigned char)v; }
            for (int i = 0; i < TOPK; i++) t->bestsc[i] = -1.0;
        }
    }
    fclose(f);
    if (TOPK > MAXK) TOPK = MAXK;
    for (int i = 0; i < 80; i++) lut[i] = (unsigned char)(i % 26);

    unsigned char k[MAXN], pr[MAXL];
    long long done = 0;
    if (enumerate) {
        long long total = 1;
        for (int i = 0; i < L; i++) total *= MOD;
        memset(pr, 0, sizeof(pr));
        for (long long it = 0; it < total; it++) {
            memcpy(k, pr, L);
            genkey(k);
            score_all(k, pr);
            int p = L - 1;
            while (p >= 0) { if (++pr[p] < MOD) break; pr[p] = 0; p--; }
            if ((++done & 0xFFFFF) == 0) fprintf(stderr, "\r%lld/%lld", done, total), fflush(stderr);
        }
    } else {
        for (int i = 0; i < nlist; i++) {
            memcpy(pr, plist + (size_t)i*L, L);
            memcpy(k, pr, L);
            genkey(k);
            score_all(k, pr);
        }
        done = nlist;
    }
    fprintf(stderr, "\n");
    printf("EXECUTED %lld\n", done);
    for (int ti = 0; ti < NT; ti++) {
        Target *t = &T[ti];
        double m = t->sum / t->cnt;
        double sd = t->sumsq / t->cnt - m * m; sd = sd > 0 ? sqrt(sd) : 0.0;
        printf("TARGET %s n=%d count=%lld mean=%.6f sd=%.6f\n", t->name, t->n, t->cnt, m, sd);
        for (int j = 0; j < TOPK; j++) {
            if (t->bestsc[j] < 0) break;
            printf("TOP %d %.6f", j, t->bestsc[j]);
            for (int q = 0; q < L; q++) printf(" %d", t->bestpr[j][q]);
            printf("\n");
        }
    }
    return 0;
}
