"""
Camada de acesso a dados (Repositories)

Este módulo concentra toda a lógica de consulta ao SAP HANA.  
Mantém um **BaseRepository** genérico (mapeia SQL → DTO) e três
repositórios concretos usados na aplicação GIP Bot:

* EventoRepository         – busca os eventos configurados no SAP B1  
* PedidoCompraRepository   – executa SQL dinâmico salvo no evento  
* UsuarioRepository        – resolve e-mails a partir de UserCodes

Se quiser adicionar novos repositórios, basta criar uma classe que
herde de BaseRepository e implemente seus métodos de consulta.
"""

from __future__ import annotations

from typing import List, Type, Any, Tuple, Optional
from dataclasses import fields

from conexao import HanaRepository           # wrapper de conexão/consulta
from dto import Evento, DocFinanceiro, Usuario, UsuarioEvento


# ──────────────────────────────────────────────
# BASE
# ──────────────────────────────────────────────
class BaseRepository(HanaRepository):
    """
    Classe base que delega ao método protegido _query, já implementado
    em `HanaRepository` (conexao.py), o trabalho de executar a consulta
    e mapear as linhas para instâncias de DTO.
    """

    def _map(self, sql: str, dto_cls: Type) -> List[Any]:
        """Executa *sql* e devolve lista de `dto_cls`."""
        return self._query(sql, dto_cls)
    
    def _map_params(self,sql: str,params: Tuple[Any, ...],dto_cls: Type,) -> List[Any]:
        """Executa *sql* com *params* e devolve lista de `dto_cls`."""
        return self._query(sql, dto_cls, params=params)


# ──────────────────────────────────────────────
# EVENTOS
# ──────────────────────────────────────────────
class EventoRepository(BaseRepository):
    """
    Lê a tabela OUQR (SAP B1) e devolve objetos `Evento`
    que contêm tanto o SQL dinâmico do alerta quanto
    metadados como assunto, template, etc.
    """

    _SQL = """
		SELECT  OUQR."IntrnalKey",
		        OUQR."QCategory",
		        OUQR."QName",
		        OUQR."QString",
		        EM."Cabecalho",
		        EM."Mensagem",
		        EM."Rodape",
		        EM."NotificarCriador",
		        EM."NotificarAprovador",
                EM."NotificarGestor"
		  FROM      "SBOTRUSTAGRO".OUQR
		  LEFT JOIN "SBOTRUSTAGRO"."EVENTOS_MENSAGENS" EM ON OUQR."IntrnalKey" = EM."IntrnalKey" 
		WHERE  "QCategory" = 27  
    """

    def all_eventos(self) -> List[Evento]:
        return self._map(self._SQL, Evento)


# ──────────────────────────────────────────────
# PEDIDO DE COMPRA (SQL dinâmico)
# ──────────────────────────────────────────────
class DocFinanRepository(BaseRepository):
    """
    Executa o SQL armazenado em `Evento.QString` e devolve
    objetos `DocFinanceiro` prontos para preenchimento dos
    placeholders no corpo do e-mail.
    """

    def documents(self, dynamic_sql: str) -> List[DocFinanceiro]:
        return self._map(dynamic_sql, DocFinanceiro)


# ──────────────────────────────────────────────
# USUÁRIOS (e-mail por UserCode)
# ──────────────────────────────────────────────
class UsuarioRepository(BaseRepository):
    """
    Resolve lista de endereços de e-mail a partir dos
    códigos de usuário (`USER_CODE`) cadastrados no SAP.
    """

    _SQL_USER_BY_CODE = """
         SELECT USR.USER_CODE AS "UserCode",
                USR.U_NAME    AS "UserName",
                USR."E_Mail"  AS "email",
                USR.SUPERUSER AS "Superuser",
                USR."PortNum" AS "telefone"
        FROM "SBOTRUSTAGRO".OUSR USR 
        WHERE USR."E_Mail" IS NOT NULL
        AND USR."E_Mail" <> ''
        AND USR.USER_CODE = ?
    """

    _SQL_ALL_USERS = """
        SELECT  USER_CODE AS "UserCode",
                U_NAME    AS "UserName",
                "E_Mail"  AS "email",
                SUPERUSER AS "Superuser",
                "PortNum" AS "telefone" 
          FROM "SBOTRUSTAGRO".OUSR
        WHERE "E_Mail" <> '' 
          AND "E_Mail" IS NOT NULL     
    """

    _SQL_SELECTED_USERS = """
        SELECT  SEL."Evento",
                USR.USER_CODE AS "UserCode",
                USR.U_NAME    AS "UserName",
                USR."E_Mail"  AS "email",
                USR.SUPERUSER AS "Superuser",
                USR."PortNum" AS "telefone"
          FROM "SBOTRUSTAGRO"."USUARIOS_SELECIONADOS" SEL 
		  LEFT JOIN "SBOTRUSTAGRO".OUSR USR ON SEL."UserCode" = USR.USER_CODE 
        WHERE "E_Mail" <> '' 
          AND "E_Mail" IS NOT NULL  
    """

    _SQL_EVENT_USER = """
        SELECT  SEL."Evento",
                USR.USER_CODE AS "UserCode",
                USR.U_NAME    AS "UserName",
                USR."E_Mail"  AS "email",
                USR.SUPERUSER AS "Superuser",
                USR."PortNum" AS "telefone"
          FROM "SBOTRUSTAGRO"."USUARIOS_SELECIONADOS" SEL
          LEFT JOIN "SBOTRUSTAGRO".OUSR USR ON SEL."UserCode" = USR.USER_CODE
         WHERE USR."E_Mail" IS NOT NULL
           AND USR."E_Mail" <> ''
           AND SEL."Evento" = ?                       -- ← placeholder certo
    """
    def emails_por_usercodes(self, codes: List[str]) -> List[str]:
        if not codes:
            return []

        quoted = ",".join(f"'{c.strip()}'" for c in set(codes))
        registros = self._map(self._SQL_BASE.format(codes=quoted), Usuario)
        return [u.email for u in registros if u.email]
    
    def all_users(self) -> List[Usuario]:
        return self._map(self._SQL_ALL_USERS, Usuario)
    
    def selected_users(self) -> List[UsuarioEvento]:
        return self._map(self._SQL_SELECTED_USERS, UsuarioEvento)
    
    def user_by_event(self, evento_key: str) -> List[UsuarioEvento]:
        return self._map_params(self._SQL_EVENT_USER,(evento_key,),UsuarioEvento)
    
    def user_by_code(self, user_code: str) -> Optional[Usuario]:
        result = self._map_params(self._SQL_USER_BY_CODE, (user_code,), Usuario)
        return result[0] if result else None
            


# ──────────────────────────────────────────────
# EXPORTS
# ──────────────────────────────────────────────
__all__ = [
    "BaseRepository",
    "EventoRepository",
    "PedidoCompraRepository",
    "UsuarioRepository",
]
