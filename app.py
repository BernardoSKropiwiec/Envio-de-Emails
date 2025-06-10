from flask import Flask, render_template, request, redirect, url_for, session, flash
import conexao
from conexao import hana_connection
from repositories import UsuarioRepository, EventoRepository


app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Tela de login
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        company_db = request.form["company_db"]

        # Autentica no Service Layer
        session_id = conexao.LogaServiceLayer(username, password, company_db)
        if session_id:
            session["session_id"] = session_id
            return redirect(url_for("exibir_usuarios"))
        else:
            flash("Falha no login. Verifique suas credenciais.", "danger")
    
    return render_template("login.html")

# Lista de usuários após login
@app.route("/usuarios")
def exibir_usuarios():
    if "session_id" not in session:
        return redirect(url_for("login"))
    
    with hana_connection() as conn:
        usuarios = UsuarioRepository(conn).all_users()
        selecoes = UsuarioRepository(conn).selected_users()
        eventos  = EventoRepository(conn).all_eventos()
    
    return render_template("index.html", usuarios=usuarios, eventos=eventos, selecoes=selecoes)

@app.route("/atualizar", methods=["POST"])
def atualizar_registros():
    if "session_id" not in session:
        return redirect(url_for("login"))
    
    # Atualiza USUARIOS_SELECIONADOS via MERGE
    selecoes = request.form.getlist("destinatarios[]")
    for selecao in selecoes:
        # Cada seleção está no formato: evento|usercode|email|flag
        evento, usercode, email, flag = selecao.split("|")
        print(selecao)
        conexao.merge_usuario_selecionado(evento, usercode, email, flag)
    
    # Atualiza EVENTOS_MENSAGENS via MERGE para cada evento
    # Coletamos os IDs dos eventos presentes no formulário (a partir da chave 'mensagem-...')
    event_ids = set()
    for key in request.form.keys():
        if key.startswith("mensagem-"):
            event_ids.add(key.split("-")[1])
    
    for evento_id in event_ids:
        cabecalho = request.form.get(f"cabecalho-{evento_id}", "")
        mensagem = request.form.get(f"mensagem-{evento_id}", "")
        rodape = request.form.get(f"rodape-{evento_id}", "")
        criador_key = f"notificar-criador-{evento_id}"
        aprovador_key = f"notificar-aprovador-{evento_id}"
        gestor_key = f"notificar-gestor-{evento_id}"
        notificarCriador = "S" if criador_key in request.form else "N"
        notificarAprovador = "S" if aprovador_key in request.form else "N"
        notificarGestor = "S" if gestor_key in request.form else "N"
        conexao.merge_evento_mensagem(evento_id, cabecalho, mensagem, rodape, notificarCriador, notificarAprovador, notificarGestor)
    
    #flash("Registros atualizados com sucesso.", "success")
    return redirect(url_for("exibir_usuarios"))



@app.route("/logout")
def logout():
    session.pop("session_id", None)
    #flash("Logout realizado com sucesso.", "success")
    return redirect(url_for("login"))

if __name__ == "__app__":
    app.run(debug=True)
