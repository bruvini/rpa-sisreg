"""Rótulos de interface — não alteram estados persistidos nem decisões técnicas."""
ESTADOS = {
    'AGUARDA_PREPARACAO': 'Aguardando conferência',
    'PRONTO_PARA_CONFERENCIA': 'Pronto para conferir',
    'DOCUMENTO_PDF_LOCALIZADO': 'Documento encontrado no espelho',
    'DOCUMENTO_VALIDADO_POR_AIH_E_NOME': 'Documento confirmado no espelho',
    'DOCUMENTO_NAO_CLASSIFICADO': 'Documento precisa de revisão',
    'PDF_SEM_DOCUMENTO_VALIDO': 'Espelho sem documento válido',
    'AIH_AUSENTE_NO_PDF': 'AIH não encontrada no PDF',
    'NOME_DIVERGENTE_ESPELHO': 'Nome diferente no espelho',
    'NOME_AUSENTE_NO_ESPELHO': 'Espelho sem nome do paciente',
    'ESPELHOS_CONFLITANTES': 'Espelhos com dados conflitantes',
    'CPF_CONFLITANTE_PDF': 'CPF diferente no espelho',
    'CNS_CONFLITANTE_PDF': 'CNS diferente no espelho',
    'CPF_HOSPITAL_INVALIDO': 'CPF inválido na planilha',
    'CNS_HOSPITAL_INVALIDO': 'CNS inválido na planilha',
    'AIH_FORMATO_INVALIDO': 'AIH em formato inválido',
    'NOME_NAO_INFORMADO': 'Nome não informado',
    'CNS_CONFIRMADO_SISREG': 'CNS localizado e conferido',
    'CNS_CONFIRMADO_OPERADORA': 'CNS confirmado pela operadora',
    'CNS_CONFLITO_SISREG': 'CNS diferente do cadastro',
    'DADOS_COLETADOS_SEM_DIVERGENCIA': 'Sem divergência nos campos consultados',
    'PENDENTE_PROCEDIMENTO_DIVERGENTE': 'Procedimento precisa de revisão',
}
MOTIVOS = {
    'NOME_NAO_CONFIRMADO_RESULTADO': 'Não foi possível confirmar o nome no resultado',
    'NOME_DIVERGENTE_RESULTADO': 'Nome diferente no resultado do SISREG',
    'CNS_DESTACADO_AMBIGUO_OU_AUSENTE': 'CNS não identificado com segurança',
    'CNS_NAO_IDENTIFICADO_DOM': 'Tela não apresentou CNS reconhecível',
    'CNS_NAO_UNICO_OU_NAO_IDENTIFICADO': 'CNS ausente ou múltiplo no resultado',
    'CPF_DIVERGENTE_CADASTRO': 'CPF diferente no cadastro',
    'CPF_NAO_CONFIRMADO_RESULTADO': 'CPF não identificado na ficha cadastral',
    'FICHA_CADASTRO_NAO_IDENTIFICADA': 'Ficha cadastral não encontrada',
    'CPF_PESQUISADO_NAO_CONFIRMADO': 'CPF pesquisado não confirmado',
    'FALHA_DE_NAVEGACAO_OU_TEMPO': 'Erro ou demora na consulta ao SISREG',
}


def rotulo_situacao(codigo: str) -> str:
    """Texto para tela; planilha continua guardando código rastreável."""
    if codigo in ESTADOS:
        return ESTADOS[codigo]
    if codigo.startswith('PENDENTE_'):
        return MOTIVOS.get(codigo[len('PENDENTE_'):], 'Requer análise do fiscal')
    return MOTIVOS.get(codigo, 'Requer revisão' if codigo else 'Aguardando')
