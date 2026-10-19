"""Leitura local, somente textual, de espelhos SIHD2 em PDF.

Não executa OCR, não consulta terceiros e não transforma CNS em CPF.
A extração é por número da AIH, com página e conflitos preservados.
"""
from __future__ import annotations
from dataclasses import dataclass
import re
import unicodedata
from pathlib import Path

RE_AIH = re.compile(r'\b(?:N[uú]m(?:ero)?\.?\s*(?:da\s*)?AIH|N[ºo]\s*AIH)\s*[:\-]?\s*([0-9][\d.\- ]{11,18})', re.I)
RE_PAC = re.compile(r'(?im)^\s*Paciente\s*:\s*(.*?)\s*$')
RE_DOC = re.compile(r'(?i)\bCNS\s*/\s*CPF\s*:\s*([0-9][0-9.\-/ ]{10,24})')


def digitos(v: object) -> str:
    if v is None:
        return ''
    return re.sub(r'\D', '', str(v))


def normalizar_aih(v: object) -> str:
    """AIH = 13 dígitos; hífen do dígito verificador é irrelevante."""
    txt = digitos(v)
    return txt if len(txt) == 13 else ''


def normalizar_nome(v: object) -> str:
    txt = unicodedata.normalize('NFKD', str(v or ''))
    txt = ''.join(ch for ch in txt if not unicodedata.combining(ch))
    return ' '.join(re.sub(r'[^A-Z ]', ' ', txt.upper()).split())


def cpf_valido(valor: object) -> bool:
    c = digitos(valor)
    if len(c) != 11 or len(set(c)) == 1:
        return False
    for tamanho in (9, 10):
        soma = sum(int(c[i]) * (tamanho + 1 - i) for i in range(tamanho))
        dv = (soma * 10) % 11
        if dv == 10:
            dv = 0
        if dv != int(c[tamanho]):
            return False
    return True


def cns_formato(valor: object) -> bool:
    return len(digitos(valor)) == 15


@dataclass(frozen=True)
class Espelho:
    aih: str
    nome: str
    cpf: str
    cns: str
    pagina: int
    rotulo_documento: str


def extrair_texto_paginas(paginas: list[str]) -> dict[str, list[Espelho]]:
    """Recebe páginas extraídas e indexa uma vez por AIH; não resolve conflitos."""
    encontrados: dict[str, list[Espelho]] = {}
    for numero, texto in enumerate(paginas, 1):
        marcadores = list(RE_AIH.finditer(texto))
        for i, m in enumerate(marcadores):
            aih = normalizar_aih(m.group(1))
            if not aih:
                continue
            trecho = texto[m.end():marcadores[i + 1].start() if i + 1 < len(marcadores) else len(texto)]
            # Campos sempre no bloco referente à AIH, nunca coletados da página inteira.
            paciente = RE_PAC.search(trecho)
            doc = RE_DOC.search(trecho)
            nome = re.split(r'\s{2,}(?:Doc|Tipo\s+doc|Sexo|Nacionalidade)\s*:', paciente.group(1), maxsplit=1, flags=re.I)[0].strip() if paciente else ''
            informado = digitos(doc.group(1)) if doc else ''
            cpf = informado if cpf_valido(informado) else ''
            cns = informado if cns_formato(informado) else ''
            e = Espelho(aih, nome, cpf, cns, numero, informado)
            encontrados.setdefault(aih, []).append(e)
    return encontrados


def ler_espelhos_pdf(caminho: str | Path) -> tuple[dict[str, list[Espelho]], list[str]]:
    """PDF textual apenas. Se imagem, pede PDF pesquisável (sem OCR invasivo)."""
    import fitz  # PyMuPDF; import tardio para facilitar testes offline
    caminho = Path(caminho)
    avisos: list[str] = []
    paginas: list[str] = []
    with fitz.open(str(caminho)) as pdf:
        if pdf.is_encrypted:
            raise ValueError('PDF protegido por senha: não foi possível ler.')
        for pg in pdf:
            paginas.append(pg.get_text('text', sort=True))
    if not any(RE_AIH.search(t) for t in paginas):
        avisos.append('Não foram reconhecidos espelhos textuais. Confirmar se PDF é pesquisável e estrutura real.')
    return extrair_texto_paginas(paginas), avisos


def escolher_espelho(registros: list[Espelho], paciente_hospital: str) -> tuple[Espelho | None, str]:
    """Repetição exata permitida; candidatos divergentes bloqueiam uso automático."""
    if not registros:
        return None, 'AIH_AUSENTE_NO_PDF'
    unico = {(normalizar_nome(r.nome), r.cpf, r.cns) for r in registros}
    if len(unico) > 1:
        return None, 'ESPELHOS_CONFLITANTES'
    e = registros[0]
    if not e.nome:
        return None, 'NOME_AUSENTE_NO_ESPELHO'
    if normalizar_nome(e.nome) != normalizar_nome(paciente_hospital):
        return None, 'NOME_DIVERGENTE_ESPELHO'
    if not (e.cpf or e.cns):
        return e, 'DOCUMENTO_NAO_CLASSIFICADO'
    return e, 'DOCUMENTO_VALIDADO_POR_AIH_E_NOME'
