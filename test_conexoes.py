# test_socketio_corrigido.py
import socketio
import threading
import time
import random

def test_player_connection(user_id):
    """Testa conexão Socket.IO com event handlers corrigidos"""
    try:
        # Cria cliente Socket.IO
        sio = socketio.Client(logger=False, engineio_logger=False)
        
        connected = False
        login_success = False
        questions_answered = 0
        
        @sio.event
        def connect():
            nonlocal connected
            connected = True
            print(f"✅ Usuário {user_id}: Conectado ao servidor")
            # Faz login imediatamente após conectar
            sio.emit('player_join', {'nickname': f'Player_{user_id}'})
        
        @sio.event
        def connect_error(data):
            print(f"❌ Usuário {user_id}: Erro de conexão - {data}")
        
        @sio.event
        def disconnect():
            nonlocal connected
            connected = False
            print(f"⚠️ Usuário {user_id}: Desconectado")
        
        @sio.on('join_success')
        def on_join_success(data):
            nonlocal login_success
            login_success = True
            print(f"🎮 Usuário {user_id}: Login OK - Nickname: {data.get('nickname', '')}")
        
        @sio.on('show_question')
        def on_show_question(data):
            print(f"❓ Usuário {user_id}: Recebeu pergunta - {data.get('text', '')[:30]}...")
            # Responde aleatoriamente após 1-3 segundos
            options_count = len(data.get('options', []))
            if options_count > 0:
                time.sleep(random.uniform(1, 3))
                answer_index = random.randint(0, options_count - 1)
                sio.emit('submit_answer', {'option_index': answer_index})
                print(f"📝 Usuário {user_id}: Respondeu opção {answer_index}")
        
        @sio.on('answer_received')
        def on_answer_received(data):
            nonlocal questions_answered
            questions_answered += 1
            print(f"📨 Usuário {user_id}: Resposta confirmada")
        
        @sio.on('show_results')
        def on_show_results(data):
            score = data.get('scores', {}).get(sio.get_sid(), 0)
            print(f"📊 Usuário {user_id}: Resultados - Score: {score}")
        
        @sio.on('game_over')
        def on_game_over(data):
            print(f"🏁 Usuário {user_id}: Jogo finalizado")
        
        @sio.on('game_reset')
        def on_game_reset(data):
            print(f"🔄 Usuário {user_id}: Jogo reiniciado")
        
        # Conecta ao servidor
        print(f"🔗 Usuário {user_id}: Conectando...")
        sio.connect('http://localhost:5000', wait_timeout=10)
        
        # Aguarda um pouco para ver se o login foi bem-sucedido
        time.sleep(2)
        
        if connected and login_success:
            print(f"🎯 Usuário {user_id}: Sessão ativa - Mantendo conexão por 45s")
            # Mantém a conexão por 45 segundos para capturar mais eventos
            time.sleep(45)
        else:
            print(f"⚠️ Usuário {user_id}: Conexão/login incompleto - Mantendo 15s")
            time.sleep(15)
        
        # Desconecta
        sio.disconnect()
        print(f"✅ Usuário {user_id}: Teste concluído - {questions_answered} perguntas respondidas")
        
    except Exception as e:
        print(f"❌ Usuário {user_id}: ERRO - {e}")

def test_simple_connection(user_id):
    """Teste mais simples apenas para verificar conexão básica"""
    try:
        sio = socketio.Client()
        
        @sio.event
        def connect():
            print(f"✅ {user_id}: Conectado!")
            sio.emit('player_join', {'nickname': f'Simple_{user_id}'})
        
        @sio.event
        def connect_error(data):
            print(f"❌ {user_id}: Erro conexão - {data}")
        
        @sio.on('join_success')
        def on_join_success(data):
            print(f"✅ {user_id}: Login confirmado")
        
        sio.connect('http://localhost:5000', wait_timeout=10)
        print(f"✅ {user_id}: Handshake OK")
        
        # Mantém por 20 segundos
        time.sleep(20)
        
        sio.disconnect()
        print(f"✅ {user_id}: Conexão básica OK")
        
    except Exception as e:
        print(f"❌ {user_id}: FALHA - {e}")

# Teste principal
if __name__ == "__main__":
    print("🚀 INICIANDO TESTE DE CONEXÕES SOCKET.IO CORRIGIDO")
    print("=" * 50)
    
    # Teste com número menor de conexões primeiro
    num_connections = 40
    print(f"📊 Testando {num_connections} conexões simultâneas...")
    
    threads = []
    for i in range(num_connections):
        t = threading.Thread(target=test_player_connection, args=(i,))
        threads.append(t)
        t.start()
        time.sleep(0.15)  # Pequeno delay entre conexões
    
    # Aguarda todas as threads
    for t in threads:
        t.join()
    
    print("=" * 50)
    print("🎉 TESTE CONCLUÍDO!")