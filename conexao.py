import warnings
import requests

from hdbcli      import dbapi
import smtplib
from email.mime.text      import MIMEText
from email.mime.multipart import MIMEMultipart

from typing      import Type, List, Any, Optional, Tuple
from dataclasses import fields
from dto         import Usuario, Evento
from contextlib  import contextmanager
from typing      import Generator, Type, List, Any

from config import settings

# Desativa os warnings de HTTPS não verificados (opcional)
warnings.filterwarnings("ignore", message="Unverified HTTPS request is being made")

# ──────────────────────────────────────────────
# 1) DATABASE (SAP HANA)
# ──────────────────────────────────────────────
@contextmanager
def hana_connection() -> Generator[dbapi.Connection, None, None]:
    conn = dbapi.connect(
        address=settings.db.host,
        port=settings.db.port,
        user=settings.db.user,
        password=settings.db.password,
        currentSchema = 'SBOTRUSTAGRO',    
    )
    try:
        yield conn
    finally:
        conn.close()

class HanaRepository:
    """Métodos comuns de acesso a dados via cursor."""
    def __init__(self, conn: dbapi.Connection):
        self._conn = conn

    def _query(
        self,
        sql: str,
        dto_cls: Type,
        params: Optional[Tuple[Any, ...]] = None   # ← novo argumento
    ) -> List[Any]:
        cur = self._conn.cursor()
        # se params for None executa direto; senão faz o binding seguro
        cur.execute(sql, params) if params else cur.execute(sql)
        cols        = [c[0] for c in cur.description]
        dto_fields  = {f.name for f in fields(dto_cls)}
        rows: List[Any] = []

        for r in cur.fetchall():
            rows.append(
                dto_cls(**{col: r[i] if col in dto_fields else None
                           for i, col in enumerate(cols)})
            )
        cur.close()
        return rows
    
def get_connection():
    return dbapi.connect(
        address="saphamultifazendas",   
        port=30015,          
        user="--", 
        password="--"
    )


def RetornaConsulta(query, dto_class: Type) -> List[Any]:
    results = []
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        dto_fields = {field.name for field in fields(dto_class)}
        columns = [desc[0] for desc in cursor.description]
        for row in cursor.fetchall():
            row_data = {col: row[idx] if col in dto_fields else None for idx, col in enumerate(columns)}
            for field in dto_fields:
                if field not in row_data:
                    row_data[field] = None
            dto_instance = dto_class(**row_data)
            results.append(dto_instance)
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao executar consulta: {e}")
    return results

def LogaServiceLayer(username, password, company_db):
    login_url = "--"
    payload = {
        "CompanyDB": company_db,
        "Password": password,
        "UserName": username
    }
    try:
        response = requests.post(login_url, json=payload, verify=False)
        response.raise_for_status()
        return response.json().get('SessionId')
    except requests.RequestException as e:
        print(f"Erro ao autenticar no Service Layer: {e}")
        return None
    

# ──────────────────────────────────────────────
# 3) EMAIL CLIENT
# ──────────────────────────────────────────────
class SMTPClient:
    def __init__(self, cfg=settings.smtp):
        self._cfg = cfg

    def _build_message(self, to_: list[str], subject: str,
                       html_body: str) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._cfg.user
        msg["To"] = ",".join(to_)
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        return msg

    def send(self, recipients: list[str], subject: str,
             html_body: str) -> None:
        if self._cfg.test_mode:
            recipients = [self._cfg.test_recipient]

        message = self._build_message(recipients, subject, html_body)

        with smtplib.SMTP(self._cfg.server, self._cfg.port) as srv:
            srv.starttls()
            srv.login(self._cfg.user, self._cfg.password)
            srv.sendmail(self._cfg.user, recipients, message.as_string())

# Funções de Upsert (Merge) nas tabelas de configuração

def merge_usuario_selecionado(evento, usercode, email, flag):
    # flag '1' significa que o usuário está marcado (deve ser inserido ou mantido)
    # flag '0' significa que o usuário está desmarcado (deve ser removido, se existir)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        merge_query = '''
        MERGE INTO "SBOTRUSTAGRO"."USUARIOS_SELECIONADOS" AS target
        USING (
            SELECT 
                CAST(? AS INTEGER) AS "Evento", 
                CAST(? AS NVARCHAR(50)) AS "UserCode", 
                CAST(? AS NVARCHAR(100)) AS "Email",
                ? AS "Flag"
            FROM DUMMY
        ) source
        ON target."Evento" = source."Evento" AND target."UserCode" = source."UserCode"
        WHEN MATCHED AND source."Flag" = '0' THEN 
            DELETE
        WHEN NOT MATCHED AND source."Flag" = '1' THEN 
            INSERT ("Evento", "UserCode", "Email") 
            VALUES (source."Evento", source."UserCode", source."Email")
        '''
        cursor.execute(merge_query, (evento, usercode, email, flag))
        conn.commit()
        print(f"[DEBUG] Merge para Usuário: {evento}|{usercode}|{email}|{flag} - Linhas afetadas: {cursor.rowcount}")
        cursor.close()
        conn.close()
    except Exception as e:
        print("Erro ao fazer merge em USUARIOS_SELECIONADOS:", e)

def merge_evento_mensagem(intrnalKey, cabecalho, mensagem, rodape, notificarCriador, notificarAprovador, notificarGestor):
    try:
        # Converte "S"/"N" para booleanos True/False, se necessário
        notificarCriador_bool = True if notificarCriador == "S" else False
        notificarAprovador_bool = True if notificarAprovador == "S" else False
        notificarGestor_bool = True if notificarGestor == "S" else False

        conn = get_connection()
        cursor = conn.cursor()
        merge_query = '''
        MERGE INTO "SBOTRUSTAGRO"."EVENTOS_MENSAGENS" AS target
        USING (
            SELECT 
                CAST(? AS INTEGER) AS "IntrnalKey", 
                CAST(? AS NCLOB) AS "Cabecalho", 
                CAST(? AS NCLOB) AS "Mensagem", 
                CAST(? AS NCLOB) AS "Rodape", 
                CAST(? AS BOOLEAN) AS "NotificarCriador", 
                CAST(? AS BOOLEAN) AS "NotificarAprovador",
                CAST(? AS BOOLEAN) AS "NotificarGestor"
            FROM DUMMY
        ) src
        ON target."IntrnalKey" = src."IntrnalKey"
        WHEN MATCHED THEN 
            UPDATE SET "Cabecalho" = src."Cabecalho",
                       "Mensagem" = src."Mensagem",
                       "Rodape" = src."Rodape",
                       "NotificarCriador" = src."NotificarCriador",
                       "NotificarAprovador" = src."NotificarAprovador",
                       "NotificarGestor" = src."NotificarAprovador"
        WHEN NOT MATCHED THEN 
            INSERT ("IntrnalKey", "Cabecalho", "Mensagem", "Rodape", "NotificarCriador", "NotificarAprovador","NotificarGestor")
            VALUES (src."IntrnalKey", src."Cabecalho", src."Mensagem", src."Rodape", src."NotificarCriador", src."NotificarAprovador",src."NotificarGestor")
        '''
        #print(f"[DEBUG] Merge Evento Mensagem: IntrnalKey={intrnalKey}, Cabecalho={cabecalho}, Mensagem={mensagem}, Rodape={rodape}, NotificarCriador={notificarCriador}, NotificarAprovador={notificarAprovador}")
        cursor.execute(merge_query, (intrnalKey, cabecalho, mensagem, rodape, notificarCriador_bool, notificarAprovador_bool, notificarGestor_bool))
        conn.commit()
        print(f"[DEBUG] Linhas afetadas (evento mensagem): {cursor.rowcount}")
        cursor.close()
        conn.close()
    except Exception as e:
        print("Erro ao fazer merge em EVENTOS_MENSAGENS:", e)



