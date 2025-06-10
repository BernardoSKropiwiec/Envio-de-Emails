from dataclasses import dataclass
from datetime import datetime, date

@dataclass
class DocFinanceiro:
    DocEntry:      int | None = None
    DocNum:        int | None = None
    ObjType:       str | None = None
    ObjDesc:       str | None = None
    CreateDate:    datetime | None = None
    UserCode:      str | None = None
    UserName:      str | None = None
    DocTotal:      float | None = None
    DocDate:       date | None = None
    DocDueDate:    date | None = None
    BPLId:         int | None = None
    BPLName:       str | None = None
    CardCode:      str | None = None
    CardName:      str | None = None
    DocStatus:      str | None = None
    Deptos:        str | None = None
    Comments:      str | None = None
    ItemCode:      str | None = None
    ItemName:      str | None = None
    CodAprovador:  str | None = None
    CodGestor:     str | None = None
    ResObjDesc:    str | None = None
    ResDocNum:     int | None = None
    ResDocStatus:  str | None = None
    Adtos:         str | None = None
    SttsAdtos:     str | None = None
    ResDocTotal:   float | None = None

   

@dataclass 
class Usuario:
    UserCode: str
    UserName: str
    Superuser: str
    email: str
    telefone: int

@dataclass #Usado para USUARIOS_SELECIONADOS
class UsuarioEvento(Usuario):
    Evento: str          

@dataclass()   
class Evento:
    IntrnalKey: int
    QCategory: int
    QName: str
    QString: str
    Cabecalho: str
    Mensagem: str
    Rodape: str 
    NotificarCriador: bool     
    NotificarAprovador: bool
    NotificarGestor: bool
'''
    def __post_init__(self) -> None: #Converte para boolean
        self.NotificarCriador   = str(self.NotificarCriador).upper() == "S"
        self.NotificarAprovador = str(self.NotificarAprovador).upper() == "S"
        self.NotificarGestor = str(self.NotificarGestor).upper() == "S"
'''
# Exemplo de como instanciar a classe
# requisicao_compra = PurchaseRequestDTO(DocEntry=1, DocNum=1001, DocDate=date.today(), UserSign="USR123")