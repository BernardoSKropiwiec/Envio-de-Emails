import smtplib
import dto
import conexao
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import re

smtp_server = 'smtp.office365.com'
smtp_port = 587
email_user = 'GIPBOT@trustagrocompany.com'
email_pass = 'Trust@234'

# Dicionário fixo para mapear departamentos para WtmCode
departamentos_para_wtm = {
    "DEP.19": 154,
    "DEP.20": 154,
    "DEP.1": 160,
    "DEP.10": 172,
    'DEP.4': 155,
    'DEP.6': 155,
    'DEP.14': 155,
    'DEP.21': 155,
    'DEP.22': 155,
    'DEP.23': 155,
    'DEP.7': 155, 
    'DEP.2': 158,
    'DEP.17': 159,
    'DEP.25': 159,
    'DEP.12': 161,
    'DEP.15': 161,
    'DEP.5': 162,
    'DEP.18': 164,
    'DEP.11': 165,
    'DEP.16': 165,
    'DEP.8': 175,
    'DEP.3': 175,
    'DEP.24': 175
}

def substituir_placeholders(texto, pedido):
    placeholders = re.findall(r'{(.*?)}', texto)
    for placeholder in placeholders:
        if hasattr(pedido, placeholder):
            valor = getattr(pedido, placeholder)
            if isinstance(valor, datetime):
                valor = valor.strftime('%d/%m/%Y')
            texto = texto.replace(f'{{{placeholder}}}', str(valor))
    return texto

def busca_email_por_usercode(user_code):
    query = f"""
    SELECT USER_CODE AS "UserCode",
           U_NAME    AS "UserName",
           "E_Mail"  AS "email"
      FROM "SBOTRUSTAGRO".OUSR    
    WHERE USER_CODE = '{user_code}'
    """
    resultado = conexao.RetornaConsulta(query, dto.Usuario)
    if resultado and resultado[0].email:
        return resultado[0].email
    return None

def busca_aprovadores(WtmCode):
    query = f"""
    SELECT OUSR.USER_CODE AS "UserCode"
      FROM "SBOTRUSTAGRO".OWTM
      LEFT JOIN "SBOTRUSTAGRO".WTM2 ON OWTM."WtmCode" = WTM2."WtmCode" 
      LEFT JOIN "SBOTRUSTAGRO".OWST ON WTM2."WstCode" = OWST."WstCode" 
      LEFT JOIN "SBOTRUSTAGRO".WST1 ON OWST."WstCode" = WST1."WstCode" 
      LEFT JOIN "SBOTRUSTAGRO".OUSR ON WST1."UserID"  = OUSR.USERID 
    WHERE OWTM."WtmCode" = '{WtmCode}'
    """
    aprovadores = conexao.RetornaConsulta(query, dto.Usuario)
    return [aprov.UserCode for aprov in aprovadores if aprov.UserCode]

# Carrega mensagens e usuários selecionados diretamente do banco
eventos_mensagens = conexao.le_eventos_mensagens()
usuarios_selecionados = conexao.le_usuarios_selecionados()
eventos = conexao.busca_eventos()

for evento in eventos:
    destinatarios = []
    query_evento = evento.QString
    pedidos = conexao.RetornaConsulta(query_evento, dto.PedCompraDTO)
    evento_id_str = str(evento.IntrnalKey)
    
    mensagem_evento = eventos_mensagens[evento_id_str]["Mensagem"]
    cabecalho_db = eventos_mensagens[evento_id_str]["Cabecalho"]
    rodape_db = eventos_mensagens[evento_id_str]["Rodape"]
    notificar_criador = eventos_mensagens[evento_id_str]["NotificarCriador"]
    notificar_aprovador = eventos_mensagens[evento_id_str]["NotificarAprovador"]
    
    if pedidos:
        mensagem = cabecalho_db
        for pedido in pedidos:
            mensagem += substituir_placeholders(mensagem_evento, pedido) + "\n\n"
        mensagem += rodape_db

        print(mensagem)

        # Obtém os destinatários a partir dos usuários selecionados (do banco)
        if evento_id_str in usuarios_selecionados:
            destinatarios.extend(usuarios_selecionados[evento_id_str])

        print(destinatarios)
        
        if notificar_criador == "S":
            for pedido in pedidos:
                criador_email = busca_email_por_usercode(pedido.UserCode)
                if criador_email and criador_email not in destinatarios:
                    destinatarios.append(criador_email)
        
        if notificar_aprovador == "S":
            aprovadores_emails = set()
            wtm_codes_aprovadores = set()
            for pedido in pedidos:
                if hasattr(pedido, "Deptos") and pedido.Deptos:
                    departamentos = [d.strip() for d in pedido.Deptos.split(',') if d.strip()]
                    for dep in departamentos:
                        if dep in departamentos_para_wtm:
                            wtm_codes_aprovadores.add(departamentos_para_wtm[dep])
            for wtmcode_dep in wtm_codes_aprovadores:
                aprovadores_usercodes = busca_aprovadores(wtmcode_dep)
                for user_code in aprovadores_usercodes:
                    aprovador_email = busca_email_por_usercode(user_code)
                    if aprovador_email:
                        aprovadores_emails.add(aprovador_email)
            for apr_email in aprovadores_emails:
                if apr_email not in destinatarios:
                    destinatarios.append(apr_email)
        
        if destinatarios:
            assunto = evento.QName
            msg = MIMEMultipart()
            msg['From'] = email_user
            msg['To'] = ', '.join(destinatarios)
            msg['Subject'] = assunto
            msg.attach(MIMEText(mensagem, 'html'))
            try:
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(email_user, email_pass)
                    server.sendmail(email_user, destinatarios, msg.as_string())
                print(f"E-mail enviado com sucesso para o evento {evento.IntrnalKey}!")
            except Exception as e:
                print(f"Ocorreu um erro ao enviar o e-mail para o evento {evento.IntrnalKey}: {e}")
        else:
            print(f"Nenhum destinatário encontrado para o evento {evento.IntrnalKey}.")
    else:
        print(f"Nenhum pedido encontrado para o evento {evento.IntrnalKey}.")
