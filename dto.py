from dataclasses import dataclass
from datetime import datetime, date

@dataclass
class PedCompraDTO:
    DocEntry: int         
    DocNum: int           
    CreateDate: datetime         
    UserCode: str    
    UserName: str    
    DocTotal: float
    DocDate: date
    DocDueDate: date
    BPLId: int
    BPLName: str
    CardCode: str   
    CardName: str
    Deptos: str
    Comments:str
    ItemCode: str
    ItemName: str

@dataclass
class NFEntradaDTO:
    DocEntry: int         
    DocNum: int           
    CreateDate: datetime         
    UserCode: str       
    DocTotal: float
    DocDate: date
    DocDueDate: date
    BPLId: int
    BPLName: str  
    ItemCode: str
    ItemName: str


@dataclass
class SolCompraDTO:
    DocEntry: int         
    DocNum: int           
    CreateDate: datetime         
    UserCode: str      

@dataclass 
class Usuario:
    UserCode: str
    UserName: str
    Superuser: str
    email: str
    telefone: int

@dataclass
class Evento:
    IntrnalKey: int
    QCategory: int
    QName: str
    QString: str
    NotifUsuario:str
    NofifAprovador:str



# Exemplo de como instanciar a classe
# requisicao_compra = PurchaseRequestDTO(DocEntry=1, DocNum=1001, DocDate=date.today(), UserSign="USR123")