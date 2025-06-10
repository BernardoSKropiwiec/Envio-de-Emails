import smtplib
import re
import sys

from conexao      import SMTPClient
from datetime     import datetime,date
from collections  import defaultdict
from operator     import attrgetter
from typing       import Iterable, Any
from conexao      import hana_connection
from repositories import EventoRepository, UsuarioRepository, BaseRepository, DocFinanRepository
from dto          import Evento, Usuario, UsuarioEvento, DocFinanceiro
# --------------------------
# Configurações de e-mail
# --------------------------
smtp_server = 'smtp.office365.com'
smtp_port = 587
email_user = 'GIPBOT@trustagrocompany.com'
email_pass = 'Trust@234'

test_email = 'bernardo.kropiwiec@trustagrocompany.com'

# ----------------------------------------
# Modo teste simples: basta chamar o script com --test ou -t
# ----------------------------------------
TEST_MODE = ('--test' in sys.argv) or ('-t' in sys.argv)
if TEST_MODE:
    print('[MODO TESTE] Todos os e-mails serão redirecionados para', test_email)

def dicionario(agrupador: str, documentos: Iterable[Any]) -> dict[Any, list]:
    chave = attrgetter(agrupador)          # extrai o atributo em tempo de execução
    grupos = defaultdict(list)

    for doc in documentos:
        grupos[chave(doc)].append(doc)     # adiciona ao grupo certo

    return dict(grupos)     

class MensagemBuilder:
    def __init__(self, cabecalho: str, corpo: str, rodape: str):
        self.cabecalho = cabecalho
        self.corpo = corpo
        self.rodape = rodape

    def substituir_placeholders(self, texto: str, documento):
        """Substitui placeholders dentro de chaves pelos valores correspondentes de pedido."""
        placeholders = re.findall(r'{(.*?)}', texto)
        for placeholder in placeholders:
            if hasattr(documento, placeholder):
                valor = getattr(documento, placeholder)
                if isinstance(valor, (datetime, date)):
                    valor = valor.strftime('%d/%m/%Y')
                elif isinstance(valor, (float)):
                    valor = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                elif valor is None:
                    valor = " "  # ou "" se preferir vazio
                texto = texto.replace(f'{{{placeholder}}}', str(valor))
        return texto

    def construir(self, documentos: list) -> str:
        texto = self.cabecalho
        for doc in documentos:
            texto += self.substituir_placeholders(self.corpo, doc) + "\n\n"
        texto += self.rodape
        return texto

class MensagemController:
    def __init__(self, usr_repo:UsuarioRepository, doc_repo:DocFinanRepository, smtp_client:SMTPClient):
        self.usr_repo = usr_repo
        self.doc_repo = doc_repo
        self.smtp = smtp_client

    def processar_evento(self, evento: Evento):
        documentos = self.doc_repo.documents(evento.QString)
        if not documentos:
            print(f"Nenhum documento para o evento {evento.IntrnalKey}")
            return

        usuarios_evento = self.usr_repo.user_by_event(evento.IntrnalKey)
        user_codes_evento = {u.UserCode for u in usuarios_evento}

        # Dicionários de destino
        dict_criadores = dicionario("UserCode", documentos) if evento.NotificarCriador else {}
        dict_aprovadores = dicionario("CodAprovador", documentos) if evento.NotificarAprovador else {}
        dict_gestores = dicionario("CodGestor", documentos) if evento.NotificarGestor else {}

        # Remoção de duplicações
        for code in list(dict_aprovadores):
            dict_criadores.pop(code, None)

        for code in list(dict_gestores):
            dict_criadores.pop(code, None)

        for code in user_codes_evento:
            dict_criadores.pop(code, None)
            dict_aprovadores.pop(code, None)
            dict_gestores.pop(code, None)
        
        if evento.IntrnalKey not in [544,541]:
            dict_criadores.pop('matheus.buzzeti', None)
            dict_aprovadores.pop('matheus.buzzeti', None)
            dict_gestores.pop('matheus.buzzeti', None)   

        if evento.NotificarCriador: print(dict_criadores.keys())

        # Builder da mensagem
        builder = MensagemBuilder(evento.Cabecalho, evento.Mensagem, evento.Rodape)

        # Enviar mensagens personalizadas
        for grupo, nome in [(dict_criadores, "Criador"), (dict_aprovadores, "Aprovador"), (dict_gestores, "Gestor")]:
            for user_code, docs in grupo.items():
                user = self.usr_repo.user_by_code(user_code)
                if not user or not user.email:
                    print(f"[AVISO] Usuário não encontrado ou sem e-mail: {user_code}")
                    continue
                if user and user.email:
                    conteudo = builder.construir(docs)
                    #print(f'Usuario: {user.email}')
                    #print(f'Assunto: {evento.QName} - {nome} [{evento.IntrnalKey}]')
                    #print(f'Mensagem: {docs.__len__()}')
                    self.smtp.send([user.email], f"{evento.QName} - {nome}: {user.UserName}", conteudo)

        # Enviar mensagem única para os usuários comuns
        if usuarios_evento:
            emails = [u.email for u in usuarios_evento if u.email]
            conteudo_comum = builder.construir(documentos)
            #print(f'Usuarios: {emails}')
            #print(f'Assunto: {evento.QName} [{evento.IntrnalKey}]')
            #print(f'Mensagem: {documentos.__len__()}')
            self.smtp.send(emails, f"{evento.QName}", conteudo_comum)


if __name__ == "__main__":
    with hana_connection() as conn:
        eventos = EventoRepository(conn).all_eventos()
        usr_repo = UsuarioRepository(conn)
        doc_repo = DocFinanRepository(conn)
        smtp = SMTPClient()

        if '--test' in sys.argv or '-t' in sys.argv:
            smtp._cfg.test_mode = True
            print(f"[MODO TESTE] Redirecionando e-mails para {smtp._cfg.test_recipient}")

        controller = MensagemController(usr_repo, doc_repo, smtp)

        for evento in eventos:
            controller.processar_evento(evento)


