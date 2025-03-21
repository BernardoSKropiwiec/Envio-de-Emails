from hdbcli import dbapi

# Conecte-se ao SAP HANA
conn = dbapi.connect(
    address="saphamultifazendas",   
    port=30015,          
    user="B1ADMIN", 
    password="#xGCba!6e0YvK7*"
)

cursor = conn.cursor()

try: 
# Consulta parametrizada
    sql = '''
        SELECT USERID, USER_CODE, U_NAME
        FROM "SBOTRUSTAGRO_HOM".OUSR
        WHERE "USER_CODE" = ?
    '''

    # Defina o valor do parâmetro
    valor_parametro = 'bernardo.kropiwiec'

    # Execute a consulta passando os parâmetros como uma tupla
    cursor.execute(sql, (valor_parametro,))

    # Recupere os resultados
    resultados = cursor.fetchall()
    for linha in resultados:
        print(linha)
except Exception as e:
    print("Erro ao fazer merge em USUARIOS_SELECIONADOS:", e)
# Feche o cursor e a conexão
cursor.close()
conn.close()