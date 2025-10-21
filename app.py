import os
from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import json

import csv
from datetime import datetime
import os

import matplotlib
matplotlib.use('Agg')  # Usa backend sem janela (necessário no servidor)
import matplotlib.pyplot as plt

def export_scores_to_csv(scores, players):
    """Exporta os resultados do quiz para um arquivo CSV local."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"scores_{timestamp}.csv"
    filepath = os.path.join(os.path.dirname(__file__), filename)

    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Jogador', 'Pontuação'])
        for sid, score in scores.items():
            writer.writerow([players.get(sid, 'Desconhecido'), score])

    print(f"✅ Resultados exportados para {filename}")


app = Flask(__name__)
app.config['SECRET_KEY'] = 'seu-segredo-super-secreto!'
socketio = SocketIO(app)

# --- Nosso "Banco de Dados" de Perguntas ---
def load_quiz_data(filename='quiz.json'):
    """Carrega as perguntas de um arquivo JSON."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Validação simples para garantir que o arquivo tem o formato esperado
            if 'title' not in data or 'questions' not in data:
                print(f"!!! ERRO: O arquivo '{filename}' está mal formatado. Faltando 'title' ou 'questions'.")
                exit(1) # Sai do programa
            
            print(f"--- Quiz '{data['title']}' carregado com sucesso de '{filename}' ---")
            return data
            
    except FileNotFoundError:
        print(f"!!! ERRO: Arquivo do quiz '{filename}' não encontrado. !!!")
        print(f"Crie o arquivo '{filename}' no mesmo diretório do app.py.")
        exit(1) # Sai do programa
        
    except json.JSONDecodeError:
        print(f"!!! ERRO: O arquivo '{filename}' contém um JSON inválido. !!!")
        print("Use um validador de JSON online para verificar a sintaxe (aspas duplas, vírgulas, etc.).")
        exit(1) # Sai do programa

# --- Nosso "Banco de Dados" de Perguntas (Agora carregado do arquivo) ---
QUIZ_DATA = load_quiz_data()

# Você pode então usar esta variável em seu código Python.
# Exemplo:
# print(QUIZ_DATA['title'])
# print(QUIZ_DATA['questions'][0]['text'])

# --- Estado do Jogo (Armazenado em Memória) ---
game_state = {
    'host_sid': None,
    'players': {}, # Dicionário de {sid: 'nickname'}
    'current_question': -1, # -1 = Lobby, 0 = Pergunta 1, etc.
    'answers': {}, # Dicionário de {sid: option_index}
    'scores': {} # Dicionário de {sid: score}
}

# --- Rotas HTTP (Para carregar as páginas) ---

@app.route('/')
def player_join():
    """Página para o aluno entrar no jogo."""
    return render_template('player.html')

@app.route('/host')
def host_view():
    """Página para o professor controlar o jogo."""
    return render_template('host.html', quiz_title=QUIZ_DATA['title'])

# --- Eventos WebSocket (A mágica em tempo real) ---

@socketio.on('connect')
def on_connect():
    """Alguém se conectou (pode ser host ou player)."""
    print(f"Cliente conectado: {request.sid}")

@socketio.on('disconnect')
def on_disconnect():
    """Alguém desconectou."""
    print(f"Cliente desconectado: {request.sid}")
    if request.sid == game_state['host_sid']:
        print("!!! O ANFITRIÃO DESCONECTOU. RESETANDO O JOGO. !!!")
        # Em um app real, você trataria isso melhor
        game_state.update(host_sid=None, players={}, current_question=-1, answers={}, scores={})
        emit('game_reset', broadcast=True)
    elif request.sid in game_state['players']:
        nickname = game_state['players'].pop(request.sid, '??')
        game_state['scores'].pop(request.sid, None)
        game_state['answers'].pop(request.sid, None)
        
        # Avisa o host que o jogador saiu
        if game_state['host_sid']:
            emit('player_left', {'nickname': nickname}, to=game_state['host_sid'])
        print(f"Jogador {nickname} saiu.")

@socketio.on('host_join')
def on_host_join():
    """O professor (host) iniciou a sala."""
    game_state['host_sid'] = request.sid
    print(f"Anfitrião se juntou: {request.sid}")
    # Envia o estado atual dos jogadores (caso o host recarregue a página)
    emit('update_player_list', list(game_state['players'].values()), to=game_state['host_sid'])

@socketio.on('player_join')
def on_player_join(data):
    """Um aluno (player) tentou entrar no jogo."""
    nickname = data.get('nickname')
    if not nickname:
        return # Ignora se não tiver nickname

    print(f"Jogador {nickname} tentando entrar...")
    game_state['players'][request.sid] = nickname
    game_state['scores'][request.sid] = 0
    
    # Avisa o host que um novo jogador entrou
    if game_state['host_sid']:
        emit('update_player_list', list(game_state['players'].values()), to=game_state['host_sid'])
    
    # Confirma para o jogador que ele entrou
    emit('join_success', {'nickname': nickname}, to=request.sid)

@socketio.on('start_game')
def on_start_game():
    """Host clicou em 'Iniciar Jogo'. Vamos para a primeira pergunta."""
    if request.sid != game_state['host_sid']:
        return # Só o host pode iniciar

    print("Iniciando o jogo!")
    advance_question()

@socketio.on('next_question')
def on_next_question():
    """Host clicou em 'Próxima Pergunta'."""
    if request.sid != game_state['host_sid']:
        return
        
    advance_question()



def advance_question():
    """Função interna para avançar para a próxima pergunta."""
    game_state['answers'] = {} # Limpa as respostas anteriores
    game_state['current_question'] += 1
    
    q_index = game_state['current_question']

    if q_index >= len(QUIZ_DATA['questions']):
        print("Fim do quiz.")
        leaderboard = []
        for sid, nickname in game_state['players'].items():
            leaderboard.append({
                'nickname': nickname,
                'score': game_state['scores'].get(sid, 0)
            })
                
        leaderboard.sort(key=lambda x: x['score'], reverse=True)

        # 🔽 Exporta os resultados automaticamente ao final
        export_scores_to_csv(game_state['scores'], game_state['players'])

        # 🔽 Envia o placar final para todos
        emit('game_over', leaderboard, broadcast=True)

    else:
        # Prepara e envia a próxima pergunta
        question_data = QUIZ_DATA['questions'][q_index]
        payload = {
            'text': question_data['text'],
            'options': question_data['options'],
            'question_index': q_index,
            'total_questions': len(QUIZ_DATA['questions'])
        }
        emit('show_question', payload, broadcast=True)
        
        # Envia ao host a visão de "respostas"
        if game_state['host_sid']:
            emit('update_answer_count', {
                'answered': 0, 
                'total': len(game_state['players'])
            }, to=game_state['host_sid'])

@socketio.on('submit_answer')
def on_submit_answer(data):
    """Um jogador enviou uma resposta."""
    if request.sid not in game_state['players']:
        return # Não é um jogador

    option_index = data.get('option_index')
    game_state['answers'][request.sid] = option_index
    
    print(f"Jogador {game_state['players'][request.sid]} respondeu: {option_index}")

    # Confirma ao jogador que a resposta foi recebida
    emit('answer_received', to=request.sid)

    # Atualiza a contagem de respostas para o host
    if game_state['host_sid']:
        emit('update_answer_count', {
            'answered': len(game_state['answers']), 
            'total': len(game_state['players'])
        }, to=game_state['host_sid'])

# --- Gera o gráfico de barras com matplotlib ---
def save_answer_distribution_chart(answer_distribution, question_data, question_index):
    os.makedirs('static/graphs', exist_ok=True)
    labels = ['A', 'B', 'C', 'D'][:len(answer_distribution)]
    values = answer_distribution

    plt.figure(figsize=(5,3))
    plt.bar(labels, values, color=['#007bff', '#28a745', '#ffc107', '#dc3545'][:len(values)])
    plt.title(f"Distribuição das respostas - Pergunta {question_index + 1}")
    plt.xlabel("Alternativas")
    plt.ylabel("Número de respostas")
    plt.tight_layout()

    filename = f"static/graphs/q{question_index + 1}_results.png"
    plt.savefig(filename)
    plt.close()
    return filename


@socketio.on('show_results')
def on_show_results():
    if request.sid != game_state['host_sid']:
        return

    q_index = game_state['current_question']
    if q_index < 0 or q_index >= len(QUIZ_DATA['questions']):
        return
        
    question_data = QUIZ_DATA['questions'][q_index]
    correct_option_index = question_data['correct_option']
    correct_option_text = question_data['options'][correct_option_index] 

    # --- NOVO: contar respostas por alternativa ---
    answer_distribution = [0] * len(question_data['options'])
    for ans in game_state['answers'].values():
        try:
            answer_distribution[int(ans)] += 1
        except (ValueError, TypeError, IndexError):
            pass
    # ----------------------------------------------

    # Calcular pontuação
    for sid, answer in game_state['answers'].items():
        try:
            if int(answer) == int(correct_option_index):
                game_state['scores'][sid] = game_state['scores'].get(sid, 0) + 10
        except:
            pass

    chart_path = save_answer_distribution_chart(answer_distribution, question_data,q_index)

    payload = {
    'correct_option': correct_option_index,
    'correct_option_text': correct_option_text,
    'scores': game_state['scores'],
    'players': game_state['players'],
    'answer_distribution': answer_distribution,
    'chart_path': chart_path  # <-- adiciona o caminho da imagem
    }

    emit('show_results', payload, broadcast=True)
    print("Mostrando resultados.")


if __name__ == '__main__':
    print("Servidor Flask-Quiz iniciado!")
    print(f"Aponte seu navegador de host (professor) para: http://localhost:5000/host")
    print(f"Alunos devem acessar: http://<IP_DO_SEU_LAPTOP>:5000")
    # O host='0.0.0.0' faz o servidor ser visível na sua rede local
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)