"""Diario de sinais: o operador anota um sinal ANTES do resultado e o sistema mede depois.

Objetivo: descobrir se o "olho" do operador tem vantagem estatistica, sem vies de retrospectiva. A hora da
anotacao e o preco de entrada sao gravados automaticamente no momento em que o sinal e anotado; nao ha como
registrar um sinal passado. Logica pura (sem MT5) para ser testavel; o acesso ao MT5 fica em
tools/signal_journal.py.
"""
import csv
import math
import os
from dataclasses import asdict, dataclass, fields

from mt5bot.core import paths

FILE_NAME = "diario_sinais.csv"
OPEN, WIN, LOSS, EXPIRED = "aberto", "alvo", "stop", "expirado"


@dataclass
class Entry:
    id: int
    anotado_em_utc: int        # epoch em segundos, gravado automaticamente
    ativo: str
    tf: str
    lado: str                  # "compra" ou "venda"
    avaliacao: str             # "bom" ou "ruim"
    motivo: str
    preco_entrada: float       # ask (compra) ou bid (venda) no momento da anotacao
    stop: float
    alvo: float
    alvo_r: float              # alvo em multiplos do risco
    candle_sinal_utc: int      # abertura do ultimo candle fechado do tempo grafico
    risco_usd: float = 0.0
    status: str = OPEN
    resultado_usd: float = 0.0
    saida_em_utc: int = 0

    @property
    def direction(self) -> int:
        return 1 if self.lado == "compra" else -1


def journal_path() -> str:
    return paths.data_file(FILE_NAME)


def load(path=None) -> list:
    path = path or journal_path()
    if not os.path.exists(path):
        return []
    types = {f.name: f.type for f in fields(Entry)}
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            kw = {}
            for k, v in row.items():
                t = types.get(k)
                kw[k] = int(float(v)) if t in (int, "int") else float(v) if t in (float, "float") else v
            out.append(Entry(**kw))
    return out


def save(entries, path=None) -> str:
    path = path or journal_path()
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[f.name for f in fields(Entry)], delimiter=";")
        w.writeheader()
        for e in entries:
            w.writerow(asdict(e))
    os.replace(tmp, path)  # grava inteiro ou nada: uma queda no meio nao corrompe o diario
    return path


def default_levels(direction, entry, candle_high, candle_low, alvo_r):
    """Regra do dono: stop na maxima (venda) ou minima (compra) do candle do sinal; alvo = alvo_r x risco."""
    stop = candle_low if direction > 0 else candle_high
    risk = (entry - stop) * direction
    if risk <= 0:
        raise ValueError("O preco ja passou do stop (a maxima/minima do candle do sinal). Sinal invalido.")
    return stop, entry + direction * alvo_r * risk


def evaluate_path(direction, entry, stop, target, highs, lows, spreads):
    """Percorre candles (de bid) depois da anotacao. Devolve (status, preco de saida, indice) ou (OPEN, None, None).

    Venda: o stop e o alvo sao executados no ask (= bid + spread). No mesmo candle, o stop vem primeiro.
    """
    for i, (h, lo, s) in enumerate(zip(highs, lows, spreads)):
        if direction > 0:
            if lo <= stop:
                return LOSS, stop, i
            if h >= target:
                return WIN, target, i
        else:
            if h + s >= stop:
                return LOSS, stop, i
            if lo + s <= target:
                return WIN, target, i
    return OPEN, None, None


def binom_tail(k, n, p):
    """P(X >= k) para X ~ Binomial(n, p): chance de acertar k ou mais so por sorte."""
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def summary(entries):
    """Estatisticas por avaliacao ("bom"/"ruim") sobre as anotacoes ja encerradas."""
    out = {}
    for label in ("bom", "ruim"):
        done = [e for e in entries if e.avaliacao == label and e.status in (WIN, LOSS)]
        n = len(done)
        wins = sum(e.status == WIN for e in done)
        # empate sem custos: acerto = 1 / (1 + alvo_r); usa a media dos alvos usados
        r = sum(e.alvo_r for e in done) / n if n else 2.0
        breakeven = 1 / (1 + r)
        out[label] = dict(n=n, wins=wins, win_rate=wins / n if n else 0.0, breakeven=breakeven,
                          total_usd=sum(e.resultado_usd for e in done),
                          p_sorte=binom_tail(wins, n, breakeven) if n else 1.0)
    return out
