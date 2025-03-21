import warnings
from hdbcli import dbapi
from typing import Type, List, Any
from dataclasses import fields
import requests
from dto import Usuario, Evento

# Desativa os warnings de HTTPS não verificados (opcional)
warnings.filterwarnings("ignore", message="Unverified HTTPS request is being made")

# Função auxiliar para obter a conexão (Conexão Única)
def get_connection():
    return dbapi.connect(
        address="saphamultifazendas",   
        port=30015,          
        user="B1ADMIN", 
        password="#xGCba!6e0YvK7*"
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
    login_url = "https://saphamultifazendas:50000/b1s/v1/Login"
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

def busca_usuarios(session_id):
    users_url = "https://saphamultifazendas:50000/b1s/v1/Users?$select=UserCode,UserName,eMail,Superuser,MobilePhoneNumber&$filter=eMail ne null and eMail ne ''&$top=80"
    headers = {
        "Cookie": f"B1SESSION={session_id}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(users_url, headers=headers, verify=False)
        response.raise_for_status()
        users_data = response.json().get("value", [])
        usuarios = [
            Usuario(
                UserCode=user["UserCode"],
                UserName=user["UserName"],
                Superuser=user["Superuser"],
                email=user.get("eMail", ""),
                telefone=user.get("MobilePhoneNumber", 0)
            )
            for user in users_data
        ]
        return usuarios
    except requests.RequestException as e:
        print(f"Erro ao buscar usuários: {e}")
        return []

def busca_todos_usuarios(session_id):
    base_url = "https://saphamultifazendas:50000/b1s/v1/Users?$select=UserCode,UserName,eMail,Superuser,MobilePhoneNumber"
    headers = {
        "Cookie": f"B1SESSION={session_id}",
        "Content-Type": "application/json"
    }
    usuarios = []
    url = base_url
    while url:
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            data = response.json()
            users_data = data.get("value", [])
            usuarios.extend([
                Usuario(
                    UserCode=user["UserCode"],
                    UserName=user["UserName"],
                    Superuser=user["Superuser"],
                    email=user.get("eMail", ""),
                    telefone=user.get("MobilePhoneNumber", 0)
                )
                for user in users_data
            ])
            url = data.get("odata.nextLink")
            if url:
                url = f"https://saphamultifazendas:50000/b1s/v1/{url}"
        except requests.RequestException as e:
            print(f"Erro ao buscar usuários: {e}")
            break
    return usuarios

def verifica_superuser(session_id, username):
    users_url = f"https://saphamultifazendas:50000/b1s/v1/Users?$filter=UserName eq '{username}'&$select=Superuser"
    headers = {
        "Cookie": f"B1SESSION={session_id}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(users_url, headers=headers, verify=False)
        response.raise_for_status()
        data = response.json().get("value", [])
        if data and data[0]["Superuser"] == "Y":
            return True
    except requests.RequestException as e:
        print(f"Erro ao verificar Superuser: {e}")
    return False

def busca_eventos() -> List[Evento]:
    query = """
        SELECT "IntrnalKey",
               "QCategory",
               "QName",
               "QString"
        FROM "SBOTRUSTAGRO".OUQR 
        INNER JOIN "SBOTRUSTAGRO".OQCN ON OUQR."QCategory" = OQCN."CategoryId" 
        WHERE "CategoryId" = 27
    """
    return RetornaConsulta(query, Evento)

# Funções de leitura dos registros das tabelas de configuração

def le_usuarios_selecionados():
    selecoes = {}
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT "Evento", "UserCode", "Email" FROM "SBOTRUSTAGRO"."USUARIOS_SELECIONADOS"')
        for row in cursor.fetchall():
            evento = str(row[0])
            if evento not in selecoes:
                selecoes[evento] = []
            selecoes[evento].append(row[2])
        cursor.close()
        conn.close()
    except Exception as e:
        print("Erro ao ler USUARIOS_SELECIONADOS:", e)
    return selecoes

def le_eventos_mensagens():
    eventos_mensagens = {}
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT "IntrnalKey","Cabecalho", "Mensagem", "Rodape", "NotificarCriador", "NotificarAprovador" FROM "SBOTRUSTAGRO"."EVENTOS_MENSAGENS"')
        for row in cursor.fetchall():
            eventos_mensagens[str(row[0])] = {
                "Cabecalho": row[1],
                "Mensagem": row[2],
                "Rodape": row[3],
                "NotificarCriador": row[4],
                "NotificarAprovador": row[5]
            }
        cursor.close()
        conn.close()
    except Exception as e:
        print("Erro ao ler EVENTOS_MENSAGENS:", e)
    return eventos_mensagens

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



def merge_evento_mensagem(intrnalKey, cabecalho, mensagem, rodape, notificarCriador, notificarAprovador):
    try:
        # Converte "S"/"N" para booleanos True/False, se necessário
        notificarCriador_bool = True if notificarCriador == "S" else False
        notificarAprovador_bool = True if notificarAprovador == "S" else False

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
                CAST(? AS BOOLEAN) AS "NotificarAprovador"
            FROM DUMMY
        ) src
        ON target."IntrnalKey" = src."IntrnalKey"
        WHEN MATCHED THEN 
            UPDATE SET "Cabecalho" = src."Cabecalho",
                       "Mensagem" = src."Mensagem",
                       "Rodape" = src."Rodape",
                       "NotificarCriador" = src."NotificarCriador",
                       "NotificarAprovador" = src."NotificarAprovador"
        WHEN NOT MATCHED THEN 
            INSERT ("IntrnalKey", "Cabecalho", "Mensagem", "Rodape", "NotificarCriador", "NotificarAprovador")
            VALUES (src."IntrnalKey", src."Cabecalho", src."Mensagem", src."Rodape", src."NotificarCriador", src."NotificarAprovador")
        '''
        #print(f"[DEBUG] Merge Evento Mensagem: IntrnalKey={intrnalKey}, Cabecalho={cabecalho}, Mensagem={mensagem}, Rodape={rodape}, NotificarCriador={notificarCriador}, NotificarAprovador={notificarAprovador}")
        cursor.execute(merge_query, (intrnalKey, cabecalho, mensagem, rodape, notificarCriador_bool, notificarAprovador_bool))
        conn.commit()
        print(f"[DEBUG] Linhas afetadas (evento mensagem): {cursor.rowcount}")
        cursor.close()
        conn.close()
    except Exception as e:
        print("Erro ao fazer merge em EVENTOS_MENSAGENS:", e)

