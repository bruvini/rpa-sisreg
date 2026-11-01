"""Observação passiva do carregamento. Não resolve ou modifica reCAPTCHA."""
from urllib.parse import urlsplit
from sisreg_navigation import origem_autorizada

ROTULOS = {
    'CAPTCHA_API_DISPONIVEL':'A API do Google está disponível na página.',
    'CAPTCHA_API_AUSENTE':'A API do Google ainda não está disponível na página.',
    'CAPTCHA_IFRAME_PRESENTE':'O iframe do Google foi criado; isso não comprova que o desafio foi exibido.',
    'CAPTCHA_IFRAME_AUSENTE':'O espaço de verificação existe, mas o iframe do Google não foi criado.',
    'CAPTCHA_COMPONENTE_NAO_IDENTIFICADO':'Não foi possível identificar o componente de verificação nessa sessão.',
    'CAPTCHA_API_HTTP_OK':'O script inicial respondeu com sucesso HTTP.',
    'CAPTCHA_SCRIPT_HTTP_OK':'O recurso auxiliar respondeu com sucesso HTTP.',
    'CAPTCHA_FRAME_HTTP_OK':'O iframe respondeu com sucesso HTTP; o conteúdo visual ainda depende do Google.',
    'CAPTCHA_PAGINA_HTTP_OK':'A página de verificação do SISREG respondeu com sucesso HTTP.',
    'CAPTCHA_DOCUMENTO_PENDENTE':'A página de verificação do SISREG ainda está em carregamento.',
    'CAPTCHA_REDE_PENDENTE':'Há recurso de verificação ainda em carregamento.',
    'CAPTCHA_REDE_TIMEOUT':'Um recurso de verificação excedeu o tempo de rede.',
    'CAPTCHA_REDE_DNS':'Falhou a resolução do endereço de um recurso de verificação.',
    'CAPTCHA_REDE_TLS':'Falhou a conexão segura de um recurso de verificação.',
    'CAPTCHA_REDE_BLOQUEADA':'O navegador informou bloqueio de um recurso de verificação.',
    'CAPTCHA_REDE_FALHOU':'O navegador informou falha de rede em um recurso de verificação.',
    'CAPTCHA_HTTP_4XX':'Um recurso de verificação retornou erro HTTP de acesso ou requisição.',
    'CAPTCHA_HTTP_5XX':'Um recurso de verificação retornou erro HTTP de servidor.',
    'CAPTCHA_HTTP_429':'Um recurso de verificação retornou limite de requisições HTTP 429.',
}


def _tipo_recurso(url):
    """Descarta endereço e parâmetros; mantém somente a classe do recurso."""
    try:
        u=urlsplit(url)
        if u.scheme!='https' or u.port not in (None,443) or u.username or u.password:
            return ''
        if u.hostname=='sisregiii.saude.gov.br' and u.path=='/cgi-bin/recaptcha':
            return 'PAGINA'
        if u.hostname in ('www.google.com','www.recaptcha.net'):
            if u.path=='/recaptcha/api.js': return 'API'
            if u.path.startswith(('/recaptcha/api2/','/recaptcha/enterprise/','/recaptcha/api/fallback')):
                return 'FRAME'
        if u.hostname=='www.gstatic.com' and u.path.startswith('/recaptcha/'):
            return 'SCRIPT'
    except (ValueError,TypeError):
        pass
    return ''


def _categoria_rede(falha):
    # O texto só existe durante a classificação; nunca é devolvido ou gravado.
    t=str(falha or '').upper()
    if 'TIMED_OUT' in t or 'TIMEOUT' in t: return 'CAPTCHA_REDE_TIMEOUT'
    if 'NAME_NOT_RESOLVED' in t or 'DNS' in t: return 'CAPTCHA_REDE_DNS'
    if 'CERT_' in t or 'SSL_' in t or 'TLS' in t: return 'CAPTCHA_REDE_TLS'
    if 'BLOCKED' in t or 'ACCESS_DENIED' in t: return 'CAPTCHA_REDE_BLOQUEADA'
    return 'CAPTCHA_REDE_FALHOU'


class MonitorRecaptcha:
    def __init__(self,contexto):
        self.estados={};self.falhas=set();self.pendentes={}
        if callable(getattr(contexto,'on',None)):
            contexto.on('request',self._pedido)
            contexto.on('response',self._resposta)
            contexto.on('requestfinished',self._termino)
            contexto.on('requestfailed',self._falha)

    def _pedido(self,pedido):
        try:
            origem_autorizada(pedido)
            if (urlsplit(pedido.url).path=='/cgi-bin/recaptcha'
                    and pedido.resource_type=='document'):
                self.estados.clear();self.falhas.clear();self.pendentes.clear()
        except Exception:
            pass
        tipo=_tipo_recurso(pedido.url)
        if tipo:
            if len(self.pendentes)>=32:self.pendentes.pop(next(iter(self.pendentes)))
            self.pendentes[id(pedido)]=tipo

    def _resposta(self,resposta):
        tipo=_tipo_recurso(resposta.url)
        if not tipo:return
        status=resposta.status
        categoria=('CAPTCHA_HTTP_429' if status==429 else
                   'CAPTCHA_HTTP_5XX' if status>=500 else
                   'CAPTCHA_HTTP_4XX' if status>=400 else
                   f'CAPTCHA_{tipo}_HTTP_OK' if 200<=status<300 else '')
        if categoria:
            self.estados[tipo]=categoria
            if status>=400:self.falhas.add(categoria)

    def _termino(self,pedido):
        self.pendentes.pop(id(pedido),None)

    def _falha(self,pedido):
        tipo=_tipo_recurso(pedido.url)
        self._termino(pedido)
        if tipo:
            categoria=_categoria_rede(pedido.failure)
            self.estados[tipo]=categoria;self.falhas.add(categoria)

    def resumo(self,contexto):
        categorias=set(self.estados.values())|self.falhas
        if self.pendentes:categorias.add('CAPTCHA_REDE_PENDENTE')
        if 'PAGINA' in self.pendentes.values():categorias.add('CAPTCHA_DOCUMENTO_PENDENTE')
        componente=False
        for pagina in getattr(contexto,'pages',[]):
            for quadro in getattr(pagina,'frames',[pagina]):
                try:
                    origem_autorizada(quadro)
                    if quadro.locator('.g-recaptcha').count()==0:continue
                    componente=True
                    api=quadro.evaluate("() => typeof window.grecaptcha !== 'undefined' && typeof window.grecaptcha.render === 'function'")
                    categorias.add('CAPTCHA_API_DISPONIVEL' if api is True else 'CAPTCHA_API_AUSENTE')
                    tem_frame=quadro.locator('.g-recaptcha iframe').count()>0
                    categorias.add('CAPTCHA_IFRAME_PRESENTE' if tem_frame else 'CAPTCHA_IFRAME_AUSENTE')
                except Exception:
                    continue
        if not componente:categorias.add('CAPTCHA_COMPONENTE_NAO_IDENTIFICADO')
        return sorted(categorias)
